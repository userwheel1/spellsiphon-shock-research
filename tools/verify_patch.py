#!/usr/bin/env python3
"""
verify_patch.py - independent structural verification of the built patch plugins.

No xEdit required.  For every plugin in dist/ it proves:

  1. valid TES4 header: form version 44, Spellsiphon.esp declared as a master
  2. exactly one top-level GRUP (type group) and only EFSH records inside
  3. every record is an EFSH override of a FormID that SpellSiphon.esp owns
  4. no record introduces new content: FormIDs must exist in Spellsiphon.esp
  5. only presentation subrecords are written (EDID/ICON/ICO2/NAM7/NAM8/NAM9/
     DATA) - never VMAD, never gameplay data
  6. no gameplay record types are present anywhere (MGEF, SPEL, PERK, ...)
  7. texture subrecords and DATA payloads match the declared vanilla source
  8. 'minimal'-style variants keep SpellSiphon's DATA byte-for-byte

Exit code 0 = all checks passed.
"""
from __future__ import annotations

import os
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

SPELLSIPHON_ESP = SPELLSIPHON_ESP
SKYRIM_ESM = SKYRIM_ESM

PRESENTATION_SUBRECORDS = {b'EDID', b'ICON', b'ICO2', b'NAM7', b'NAM8', b'NAM9', b'DATA'}
GAMEPLAY_SIGS = {b'MGEF', b'SPEL', b'SCRL', b'ENCH', b'PERK', b'QUST', b'KYWD',
                 b'GLOB', b'FLST', b'BOOK', b'SHOU', b'WEAP', b'ARMO', b'VMAD'}

VANILLA_SOURCE = {
    'vanilla': 0x0010BEAC,
    'minimal': 0x0010BEAC,
    'mage': 0x00094160,
    'both': 0x0010BEAC,
    'life': 0x0010BEAC,
    'life-switch': 0x0010BEAC,
}

FOLDER_TO_VARIANT = [
    ('All Life + Switch', 'life-switch'),
    ('All Life Shaders', 'life'),
    ('Both Shaders', 'both'),
    ('Vanilla Shock', 'vanilla'),
    ('Mage Glow', 'mage'),
    ('Minimal', 'minimal'),
]


def read(path: str) -> bytes:
    with open(path, 'rb') as fh:
        return fh.read()


def iter_top(buf: bytes):
    size = struct.unpack_from('<I', buf, 4)[0]
    start, n = 24 + size, len(buf)

    def walk(s: int, e: int, depth: int):
        o = s
        while o + 24 <= e:
            sig = buf[o:o + 4]
            sz = struct.unpack_from('<I', buf, o + 4)[0]
            if sz < 24 or o + sz > e:
                return
            if sig == b'GRUP':
                yield ('GRUP', {'off': o, 'size': sz, 'depth': depth,
                                'label': buf[o + 8:o + 12],
                                'type': struct.unpack_from('<i', buf, o + 12)[0]})
                yield from walk(o + 24, o + sz, depth + 1)
                o += sz
            else:
                yield ('REC', {
                    'off': o, 'sig': sig, 'size': sz, 'depth': depth,
                    'formid': struct.unpack_from('<I', buf, o + 12)[0],
                    'formver': struct.unpack_from('<H', buf, o + 20)[0],
                })
                o += 24 + sz
    yield from walk(start, n, 0)


def subrecords(buf: bytes, rec_off: int, size: int):
    out, o, end = [], rec_off + 24, rec_off + 24 + size
    while o + 6 <= end:
        sig = buf[o:o + 4]
        sl = struct.unpack_from('<H', buf, o + 4)[0]
        o += 6
        out.append((sig, buf[o:o + sl]))
        o += sl
    return out


def index_records(buf: bytes):
    out = {}
    for kind, info in iter_top(buf):
        if kind == 'REC':
            out[info['formid']] = info
    return out


class Report:
    def __init__(self):
        self.checks = 0
        self.failures = 0

    def check(self, ok: bool, label: str, detail: str = ''):
        self.checks += 1
        if not ok:
            self.failures += 1
        line = f"  [{'PASS' if ok else 'FAIL'}] {label}"
        if detail:
            line += f'  ({detail})'
        print(line)


def verify(plugin_path: str, variant: str) -> bool:
    print(f'\n=== {os.path.basename(os.path.dirname(plugin_path))}   [variant: {variant}]')
    rep = Report()
    plugin = read(plugin_path)

    # --- header ---
    rep.check(plugin[:4] == b'TES4', 'file starts with a TES4 record')
    tes4_size = struct.unpack_from('<I', plugin, 4)[0]
    rep.check(struct.unpack_from('<H', plugin, 20)[0] == 44,
              'TES4 form version is 44 (SSE)')
    masters, o, end = [], 24, 24 + tes4_size
    while o + 6 <= end:
        sig = plugin[o:o + 4]
        sl = struct.unpack_from('<H', plugin, o + 4)[0]
        o += 6
        if sig == b'MAST':
            masters.append(plugin[o:o + sl].split(b'\x00')[0].decode())
        o += sl
    rep.check('Spellsiphon.esp' in masters, 'Spellsiphon.esp is declared as a master',
              ', '.join(masters))

    # --- structure ---
    items = list(iter_top(plugin))
    groups = [i for k, i in items if k == 'GRUP']
    records = [i for k, i in items if k == 'REC']
    rep.check(len(groups) == 1, 'exactly one top-level GRUP', f'found {len(groups)}')
    if groups:
        rep.check(groups[0]['label'] == b'EFSH',
                  "the GRUP is the EFSH type group",
                  groups[0]['label'].decode('latin1'))
        rep.check(groups[0]['type'] == 0, 'group type is 0 (top level)')
    rep.check(len(records) > 0, 'contains at least one record', f'{len(records)}')

    # --- index the sources ---
    ss = read(SPELLSIPHON_ESP)
    sky = read(SKYRIM_ESM)
    ss_index = index_records(ss)
    src_id = VANILLA_SOURCE.get(variant)
    src_index = index_records(sky)
    src_rec = src_index.get(src_id) if src_id else None
    src_subs = {}
    if src_rec:
        src_subs = dict(subrecords(sky, src_rec['off'], src_rec['size']))

    ok_all = True
    for rec in records:
        if rec['sig'] != b'EFSH':
            rep.check(False, 'record is an EFSH', rec['sig'].decode('latin1'))
            ok_all = False
            continue
        if rec['formid'] not in ss_index:
            rep.check(False, f"FormID {rec['formid']:08X} exists in Spellsiphon.esp "
                             f"(not a new record)")
            ok_all = False
            continue

        subs = subrecords(plugin, rec['off'], rec['size'])
        sigs = {s for s, _ in subs}
        rep.check(sigs <= PRESENTATION_SUBRECORDS,
                  f"[{rec['formid']:08X}] only presentation subrecords",
                  ', '.join(sorted(s.decode() for s in sigs)))
        rep.check(b'VMAD' not in sigs, f"[{rec['formid']:08X}] no VMAD (scripts untouched)")
        rep.check(not (sigs & GAMEPLAY_SIGS), f"[{rec['formid']:08X}] no gameplay subrecords")
        rep.check(rec['formver'] == 44, f"[{rec['formid']:08X}] form version 44")

        # EDID must be preserved (an override must not rename the record)
        tgt_rec = ss_index[rec['formid']]
        tgt_subs = dict(subrecords(ss, tgt_rec['off'], tgt_rec['size']))
        got_edid = next((p for s, p in subs if s == b'EDID'), None)
        want_edid = tgt_subs.get(b'EDID')
        rep.check(got_edid == want_edid,
                  f"[{rec['formid']:08X}] EditorID preserved",
                  (got_edid or b'').split(b'\x00')[0].decode('utf-8', 'replace'))

        if variant == 'minimal':
            got = next((p for s, p in subs if s == b'DATA'), None)
            rep.check(got is not None and got == tgt_subs.get(b'DATA'),
                      f"[{rec['formid']:08X}] DATA identical to Spellsiphon (tuning kept)")
        elif src_subs:
            got_data = next((p for s, p in subs if s == b'DATA'), None)
            rep.check(got_data == src_subs.get(b'DATA'),
                      f"[{rec['formid']:08X}] DATA matches vanilla source")
            for sig in (b'ICON', b'ICO2', b'NAM7', b'NAM8', b'NAM9'):
                got = next((p for s, p in subs if s == sig), None)
                if got is None:
                    continue
                rep.check(got == src_subs.get(sig),
                          f"[{rec['formid']:08X}] {sig.decode()} matches vanilla source")

    print(f'    -> {rep.checks - rep.failures}/{rep.checks} checks passed')
    return rep.failures == 0 and ok_all


def main() -> int:
    dist = os.path.join(PROJECT, 'dist')
    targets = []
    for folder in sorted(os.listdir(dist)):
        path = os.path.join(dist, folder)
        if not os.path.isdir(path):
            continue
        esp = os.path.join(path, 'Spellsiphon - Subtle Draw Effects.esp')
        if not os.path.isfile(esp):
            continue
        variant = next((v for pat, v in FOLDER_TO_VARIANT if pat in folder), None)
        if variant is None:
            continue
        targets.append((esp, variant))

    if not targets:
        print('no built plugins found; run build_patch.py first')
        return 1

    ok = True
    for esp, variant in targets:
        ok &= verify(esp, variant)

    print('\n' + ('ALL VARIANTS VERIFIED' if ok else 'VERIFICATION FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
