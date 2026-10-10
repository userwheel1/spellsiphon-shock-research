#!/usr/bin/env python3
"""
build_patch.py - generate the standalone SpellSiphon "Subtle Draw Effects" patch.

The patch is an ordinary (non-master) Skyrim SE plugin that overrides exactly one
record and nothing else:

    Spellsiphon.esp : EFSH "KSSC_ShockShader"  (raw FormID 0403603E)

That Effect Shader is referenced by the script property DrawShaders of
MGEF KSSC_DrawME (04002857) and MGEF KSSC_DrawDeathME (04002859).  It is the
"Life draw" (shock) view shader that builds up on screen as Woven Power stacks.

An Effect Shader is pure presentation: texture paths plus particle/emission
parameters.  It holds no gameplay data, so overriding it cannot change Woven
Power accumulation, damage, cooldowns or any other SpellSiphon mechanic.

Variants
--------
  vanilla  (recommended)
        Replace the whole record with the payload of vanilla
        EFSH AlchArmorShockFXS (Skyrim.esm 0010BEAC).  This is byte-for-byte
        the edit the (currently hidden) Nexus patch "Spellsiphon Patch -
        Reduced Life Draw Lightning Visual" describes.  Removes ShockTile01.dds
        and the GradShockHit.dds impact gradient, which are what cover the
        screen; keeps a blue shock glow via ShockParticles02.dds.

  minimal
        Keep SpellSiphon's own emission/particle tuning and change only the two
        subrecords that drive the over-bright look:
            ICON : ShockTile01.dds            -> DarkSwirls.dds
            NAM8 : GradShockHit.dds           -> GradShockEnchArmor.dds
        Smallest possible change; preserves the mod author's intent and stays
        compatible if Arctal later retunes the shader.

  mage
        Same as `vanilla` but uses vanilla MagicArmorOakFleshFXS (00094160)
        for a generic, low-key spell glow with no shock texture at all.

Usage
-----
    python build_patch.py --variant vanilla
    python build_patch.py --all
    python build_patch.py --info

Environment overrides:
    SPELLSIPHON_ESP   path to the installed Spellsiphon.esp
    SKYRIM_ESM        path to Skyrim.esm
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DIST = os.path.join(PROJECT, 'dist')

SPELLSIPHON_ESP = SPELLSIPHON_ESP
SKYRIM_ESM = SKYRIM_ESM

# --- record identities -----------------------------------------------------
TARGET_FORMID = 0x0403603E
TARGET_EDID = 'KSSC_ShockShader'

# Second shock shader: used by KSSC_DischargeME (Life Discharge) and
# KSSC_LifeCageME (Life Cage / Stasis).  It uses only ShockParticles02.dds with
# no tile texture and no gradient, so an over-bright replacement of that texture
# shows up here most starkly.
SILENT_FORMID = 0x044459F1
SILENT_EDID = 'KSSC_ShockShader_Silent'

PLUGIN_BASENAME = 'Spellsiphon - Subtle Draw Effects'

# subrecord order used by the original records; preserved in the overrides
SUBRECORD_ORDER = [b'EDID', b'ICON', b'ICO2', b'NAM7', b'NAM8', b'NAM9', b'DATA']

VARIANTS = {
    'vanilla': {
        'suffix': 'Vanilla Shock',
        'mode': 'full',
        'targets': ['main'],
        'source_formid': 0x0010BEAC,
        'source_edid': 'AlchArmorShockFXS',
        'summary': 'Vanilla shock-resist armour shader (AlchArmorShockFXS) - the '
                   'community-established fix.',
    },
    'minimal': {
        'suffix': 'Minimal',
        'mode': 'textures',
        'targets': ['main'],
        'source_formid': 0x0010BEAC,
        'source_edid': 'AlchArmorShockFXS',
        'summary': 'Only ICON and NAM8 replaced; SpellSiphon emission tuning kept.',
    },
    'mage': {
        'suffix': 'Mage Glow',
        'mode': 'full',
        'targets': ['main'],
        'source_formid': 0x00094160,
        'source_edid': 'MagicArmorOakFleshFXS',
        'summary': 'Vanilla Oakflesh shader - generic warm glow, no shock texture.',
    },
    'both': {
        'suffix': 'Both Shaders',
        'mode': 'full',
        'targets': ['main', 'silent'],
        'source_formid': 0x0010BEAC,
        'source_edid': 'AlchArmorShockFXS',
        'summary': 'Covers BOTH shock shaders - Draw AND Life Discharge / '
                   'Life Cage / Life Focus.  Widest net; use if the Draw-only '
                   'patch did not fully solve it.',
    },
    'life': {
        'suffix': 'All Life Shaders',
        'mode': 'full',
        'group': 'life',
        'source_formid': 0x0010BEAC,
        'source_edid': 'AlchArmorShockFXS',
        'summary': 'Covers ALL Life-element shaders: Draw, Life Discharge, '
                   'Elemental Overload, Life Focus, weapon imbue and '
                   'bound-weapon attunement.  This removes the persistent '
                   'electrification that builds up from stacking Woven Power.',
    },
    'life-switch': {
        'suffix': 'All Life + Switch',
        'mode': 'full',
        'group': 'life-switch',
        'source_formid': 0x0010BEAC,
        'source_edid': 'AlchArmorShockFXS',
        'summary': 'Broadest safe set: every Life shader plus the weapon/spell '
                   'switching shaders - including KSSC_WeaponSwitchShader, the '
                   'brightest record in the mod (Color Scale 4.0, pure white).',
    },
}

TEXTURE_SUBRECORDS = (b'ICON', b'ICO2', b'NAM7', b'NAM8', b'NAM9')

TARGETS = {
    'main': (TARGET_FORMID, TARGET_EDID),
    'silent': (SILENT_FORMID, SILENT_EDID),
}

# Semantic groups of Effect Shaders.
#
# SpellSiphon builds almost every "Life" (shock) visual from the same recipe:
#   ICON = ShockTile01.dds, ICO2 = ShockParticles02.dds,
#   NAM8 = GradShockHit.dds (the very bright shock-impact gradient)
# Ten records share it.  Patching only KSSC_ShockShader covers the Draw
# animation but leaves the persistent ones (weapon imbue, bound-weapon
# attunement, elemental overload, life focus) untouched.
#
# All of them were enumerated from the plugin and verified with
# tools/visual_inventory.py.
SHADER_GROUPS = {
    # The two shaders the (now hidden) Nexus patch 179927 addressed.
    'draw': [
        0x0403603E,   # KSSC_ShockShader
        0x044459F1,   # KSSC_ShockShader_Silent
    ],

    # Everything SpellSiphon draws for the LIFE (shock) element plus the
    # shock-tinted weapon visuals.  Enumerated with tools/bright_shaders.py:
    # these all use GradShockHit.dds (the very bright shock-impact gradient)
    # and/or ShockParticles02.dds / ShockTile01.dds.
    'life': [
        0x0403603E,   # KSSC_ShockShader                    Draw
        0x044459F1,   # KSSC_ShockShader_Silent             Life Discharge / Life Cage
        0x04911CE5,   # KSSC_OverloadFX_Life_Shader         Elemental Overload (Life)
        0x0496CF20,   # KSSC_BoundSoulfoci_Shader           Life Focus  (persistent)
        0x042D9C4A,   # KSSC_WeaponEnchantmentShader_Life   weapon imbue (persistent)
        0x04427EAC,   # KSSC_BoundWeaponAttunementShader_Life
        0x0457B033,   # KSSC_WeaponEnchantShader_Burst_Life
        0x046E4E1B,   # KSSC_LifeCageShader
    ],

    # Life shaders plus the weapon/spell switching visuals.  The switch shader
    # is the brightest record in the mod (Color Scale 4.0, Color Key 2 pure
    # white 255,255,255), so it is a prime suspect for a white screen fill.
    'life-switch': [
        0x0403603E, 0x044459F1, 0x04911CE5, 0x0496CF20, 0x042D9C4A,
        0x04427EAC, 0x0457B033, 0x046E4E1B,
        0x045DBB09,   # KSSC_WeaponSwitchShader            Color Scale 4.0, white
        0x04555E35,   # KSSC_SpellSwitchShader
        0x044344AF,   # KSSC_SpellSwitchShader_New
        0x04460D9E,   # KSSC_BoundWeaponAttunementShader_None
        0x04427EAB,   # KSSC_BoundWeaponAttunementShader_World
        0x04427EAD,   # KSSC_BoundWeaponAttunementShader_Death
        0x042D9C48,   # KSSC_WeaponEnchantmentShader_World
        0x042D9C49,   # KSSC_WeaponEnchantmentShader_Death
        0x0474F355,   # KSSC_WhiteCracksShader
    ],
}

GROUP_LABELS = {
    'draw': 'Draw only',
    'life': 'All Life-element shaders',
    'life-switch': 'All Life shaders + weapon/spell switch shaders',
}


# --------------------------------------------------------------------------
# plugin reading
# --------------------------------------------------------------------------
def read_file(path: str) -> bytes:
    with open(path, 'rb') as fh:
        return fh.read()


def iter_records(buf: bytes):
    off, n = 0, len(buf)
    while off + 24 <= n:
        sig = buf[off:off + 4]
        size = struct.unpack_from('<I', buf, off + 4)[0]
        if sig == b'GRUP':
            off += 24
            continue
        if off + 24 + size > n:
            break
        yield {
            'offset': off,
            'sig': sig,
            'size': size,
            'flags': struct.unpack_from('<I', buf, off + 8)[0],
            'formid': struct.unpack_from('<I', buf, off + 12)[0],
        }
        off += 24 + size


def read_subrecords(buf: bytes, rec_off: int, size: int):
    out, o, end = [], rec_off + 24, rec_off + 24 + size
    while o + 6 <= end:
        sig = buf[o:o + 4]
        sl = struct.unpack_from('<H', buf, o + 4)[0]
        o += 6
        out.append((sig, buf[o:o + sl]))
        o += sl
    return out


def find_record(buf: bytes, formid: int):
    for rec in iter_records(buf):
        if rec['formid'] == formid:
            rec['subs'] = read_subrecords(buf, rec['offset'], rec['size'])
            return rec
    return None


# --------------------------------------------------------------------------
# plugin writing
# --------------------------------------------------------------------------
def zstring(value: str) -> bytes:
    return value.encode('utf-8') + b'\x00'


def sub(sig: bytes, payload: bytes) -> bytes:
    if len(payload) > 0xFFFF:
        raise ValueError(f'subrecord {sig!r} too large ({len(payload)} bytes)')
    return sig + struct.pack('<H', len(payload)) + payload


PATCH_VERSION = '2.0.0'


def build_tes4(masters: list[str], num_records: int, next_object_id: int,
               signature: str = '') -> bytes:
    body = bytearray()
    body += sub(b'HEDR', struct.pack('<fII', 1.70, num_records, next_object_id))
    body += sub(b'CNAM', zstring('DEFAULT'))
    # SNAM carries a free-form description; it makes the installed variant
    # identifiable in xEdit / MO2, which matters because every variant ships
    # under the same plugin file name.
    if signature:
        body += sub(b'SNAM', zstring(signature))
    for master in masters:
        body += sub(b'MAST', zstring(master))
        body += sub(b'DATA', b'\x00' * 8)
    header = (b'TES4'
              + struct.pack('<I', len(body))       # data size
              + struct.pack('<I', 0)               # flags
              + struct.pack('<I', 0)               # form id
              + struct.pack('<I', 0)               # vcs
              + struct.pack('<H', 44)              # form version (SSE)
              + struct.pack('<H', 0))              # vcs2
    return header + bytes(body)


def build_record(sig: bytes, formid: int, subrecords) -> bytes:
    body = bytearray()
    for s, payload in subrecords:
        body += sub(s, payload)
    header = struct.pack('<4sIIIIHH', sig, len(body), 0, formid, 0, 44, 0)
    return header + bytes(body)


def print_label(label) -> bytes:
    return label if isinstance(label, bytes) else int(label).to_bytes(4, 'little')


def build_grup(label, content: bytes, group_type: int = 0) -> bytes:
    """Build a GRUP record.

    For a top-level "type" group (group type 0) the label bytes are the record
    signature itself, e.g. label = b'EFSH'.  Spellsiphon.esp uses exactly this
    layout, and xEdit reports the group as 'GRUP Top "EFSH"'.
    """
    header = bytearray()
    header += b'GRUP'
    header += struct.pack('<I', 24 + len(content))   # total group size
    header += print_label(label)                     # label
    header += struct.pack('<i', group_type)          # group type
    header += b'\x00' * 8                            # version control / unused
    return bytes(header) + content


def master_list_for(plugin_bytes: bytes) -> list[str]:
    """Read the master list out of a TES4 record."""
    size = struct.unpack_from('<I', plugin_bytes, 4)[0]
    o, end = 24, 24 + size
    masters = []
    while o + 6 <= end:
        sig = plugin_bytes[o:o + 4]
        sl = struct.unpack_from('<H', plugin_bytes, o + 4)[0]
        o += 6
        if sig == b'MAST':
            masters.append(plugin_bytes[o:o + sl].split(b'\x00')[0].decode('utf-8'))
        o += sl
    return masters


# --------------------------------------------------------------------------
# patch construction
# --------------------------------------------------------------------------
def build_variant(key: str) -> dict:
    spec = VARIANTS[key]
    ss = read_file(SPELLSIPHON_ESP)
    sky = read_file(SKYRIM_ESM)

    source = find_record(sky, spec['source_formid'])
    if source is None:
        raise SystemExit(
            f"source EFSH {spec['source_formid']:08X} not found in {SKYRIM_ESM}")
    src_map = {s: p for s, p in source['subs']}

    records = []          # (formid, edid, override subrecords, original subs)
    if 'group' in spec:
        target_list = [(fid, None) for fid in SHADER_GROUPS[spec['group']]]
    else:
        target_list = [TARGETS[t] for t in spec['targets']]

    for formid, edid in target_list:
        target = find_record(ss, formid)
        if target is None:
            raise SystemExit(f'target EFSH {formid:08X} not found in {SPELLSIPHON_ESP}')
        if edid is None:
            edid = next((p.split(b'\x00')[0].decode('utf-8', 'replace')
                         for s, p in target['subs'] if s == b'EDID'), f'{formid:08X}')
        tgt_map = {s: p for s, p in target['subs']}

        override = []
        for sig in SUBRECORD_ORDER:
            if sig == b'EDID':
                override.append((sig, zstring(edid)))
                continue
            if spec['mode'] == 'full':
                if sig in src_map:
                    override.append((sig, src_map[sig]))
                elif sig in tgt_map:
                    override.append((sig, tgt_map[sig]))
                else:
                    override.append((sig, b'\x00'))
            elif spec['mode'] == 'textures':
                if sig in TEXTURE_SUBRECORDS and sig in src_map:
                    override.append((sig, src_map[sig]))
                elif sig in tgt_map:
                    override.append((sig, tgt_map[sig]))
                else:
                    override.append((sig, b'\x00'))
            else:
                raise SystemExit(f"unknown mode {spec['mode']!r}")

        records.append({
            'formid': formid,
            'edid': edid,
            'override': override,
            'target_subs': target['subs'],
        })

    masters = master_list_for(ss)
    if 'Spellsiphon.esp' not in masters:
        masters = masters + ['Spellsiphon.esp']

    signature = (f'Spellsiphon - Subtle Draw Effects v{PATCH_VERSION} '
                 f'[{key}] - {len(records)} Effect Shader override(s); '
                 f'source: {spec["source_edid"]}. No gameplay records.')
    tes4 = build_tes4(masters, num_records=len(records),
                      next_object_id=max(r['formid'] for r in records) + 1,
                      signature=signature)
    content = bytearray()
    for rec in records:
        content += build_record(b'EFSH', rec['formid'], rec['override'])
    plugin = tes4 + build_grup(b'EFSH', bytes(content), group_type=0)

    return {
        'key': key,
        'spec': spec,
        'plugin': plugin,
        'masters': masters,
        'records': records,
        'source_subs': source['subs'],
    }


def summarise(result: dict) -> str:
    spec = result['spec']
    lines = [
        f"variant      : {result['key']}",
        f"file suffix  : ({spec['suffix']})",
        f"approach     : {spec['summary']}",
        f"masters      : {', '.join(result['masters'])}",
        f"records      : {len(result['records'])}",
        f"plugin size  : {len(result['plugin']):,} bytes",
    ]
    src = {s: p for s, p in result['source_subs']}
    for rec in result['records']:
        tgt = {s: p for s, p in rec['target_subs']}
        lines.append(f"  EFSH {rec['edid']} [{rec['formid']:08X}]")
        for sig, payload in rec['override']:
            name = sig.decode()
            if sig == b'DATA':
                origin = ('source (vanilla)' if spec['mode'] == 'full'
                          else 'Spellsiphon (unchanged)')
                lines.append(f"      {name:<5} {len(payload):>4} bytes   {origin}")
            else:
                text = payload.split(b'\x00')[0].decode('utf-8', 'replace')
                changed = sig in src and src[sig] != tgt.get(sig)
                flag = '  <-- changed' if changed else ''
                lines.append(f"      {name:<5} {text!r}{flag}")
    return '\n'.join(lines)


def write_variant(result: dict) -> str:
    folder = f"{PLUGIN_BASENAME} ({result['spec']['suffix']})"
    out_dir = os.path.join(DIST, folder)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'{PLUGIN_BASENAME}.esp')
    with open(path, 'wb') as fh:
        fh.write(result['plugin'])
    return path


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--variant', choices=sorted(VARIANTS))
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--info', action='store_true')
    args = ap.parse_args()

    if args.info or (not args.variant and not args.all):
        ss = read_file(SPELLSIPHON_ESP)
        for formid, edid in TARGETS.values():
            target = find_record(ss, formid)
            if target is None:
                print(f'EFSH {edid} [{formid:08X}] NOT FOUND')
                continue
            print(f'EFSH {edid} [{formid:08X}] in {SPELLSIPHON_ESP}')
            for sig, payload in target['subs']:
                shown = (payload.split(b'\x00')[0].decode('utf-8', 'replace')
                         if sig != b'DATA' else f'[{len(payload)} bytes]')
                print(f'   {sig.decode():<5} {shown}')
            print()
        return 0

    keys = sorted(VARIANTS) if args.all else [args.variant]
    for key in keys:
        result = build_variant(key)
        print(summarise(result))
        print(f'written -> {write_variant(result)}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
