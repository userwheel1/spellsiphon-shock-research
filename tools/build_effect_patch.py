"""Byte-accurate VMAD surgery: empty one object-array property.

Verified layout used here (Skyrim SE VMAD v5, from the actual bytes of
KSSC_WovenPowerVisualME):

    <u16 strlen><name bytes> 00        script or property name, NUL-terminated
    <u8 flags>                         script flags (scripts only)
    <u16 propcount>                    scripts only
    <u8 type><u8 flags>                per property
    <u32 count><count * 8 bytes>       object array payload
                                       (first dword of each entry is the FormID)

Rather than reserialising the whole block (error-prone), this patches the exact
u32 count in place and writes the record back unchanged elsewhere.
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
DIST = os.path.join(PROJECT, 'dist-effect')

SS = SPELLSIPHON_ESP

TARGET_FORMID = 0x042B4A2C
TARGET_EDID = 'KSSC_WovenPowerVisualME'
TARGET_PROP = 'EffectsToPlay'
PLUGIN_NAME = 'Spellsiphon - No Woven Power Lightning'
PATCH_VERSION = '1.0.0'


def read(p):
    with open(p, 'rb') as f:
        return f.read()


def iter_records(b):
    off, n = 0, len(b)
    while off + 24 <= n:
        sig = b[off:off + 4]
        size = struct.unpack_from('<I', b, off + 4)[0]
        if sig == b'GRUP':
            off += 24
            continue
        if off + 24 + size > n:
            break
        yield off, sig, size, struct.unpack_from('<I', b, off + 12)[0]
        off += 24 + size


def iter_subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, o, sl
        o += sl


def existing_formids(plugin: bytes) -> set[int]:
    """All FormIDs defined in a plugin (for validating a decode)."""
    out = set()
    for _off, _sig, _size, fid in iter_records(plugin):
        out.add(fid)
    return out


def object_formid(raw: bytes, at: int) -> int | None:
    """Decode one 8-byte object entry at `at`.

    Verified against real bytes of KSSC_WovenPowerVisualME:
        ... 00 00 ff ff | 0e ee 0c 00 ...
    the FormID is the SECOND dword read little-endian => 0x000CEE0E, which is
    exactly RFCT FXDragonResurStreaksEffect.
    """
    if at + 8 > len(raw):
        return None
    return struct.unpack_from('<I', raw, at + 4)[0]


def find_prop_count_offset(vmad: bytes, prop: str, known: set[int]):
    """Locate the u32 count that belongs to object-array property `prop`.

    The name encoding varies, so instead of assuming a fixed prefix this tries
    every plausible position after the name and accepts the first one that
    yields type in (1, 6, 11) and at least one FORMID that really exists.
    Returns (count_offset, count, [formids]) or (None, 0, []).
    """
    name = prop.encode()
    search = 0
    while True:
        i = vmad.find(name, search)
        if i < 0:
            return None, 0, []
        search = i + 1
        # The name is preceded by a u16 length and followed by type/flags/count,
        # but the exact prefix layout differs between writers.  Search a wide
        # window and accept the first layout whose FormIDs all resolve.
        for toff in range(0, 24):
            if i + toff >= len(vmad):
                break
            if vmad[i + toff] not in (1, 6, 11):
                continue
            for coff in range(toff + 2, toff + 8):
                if i + coff + 4 > len(vmad):
                    continue
                cnt = struct.unpack_from('<I', vmad, i + coff)[0]
                if not (1 <= cnt <= 32):
                    continue
                base = i + coff + 4
                if base + cnt * 8 > len(vmad):
                    continue
                fids = []
                for k in range(cnt):
                    fid = object_formid(vmad, base + k * 8)
                    if fid is None:
                        break
                    fids.append(fid)
                if len(fids) == cnt and all(f in known for f in fids):
                    return i + coff, cnt, fids
    return None, 0, []


# ---------------------------------------------------------------- plugin I/O
def zstring(s):
    return s.encode('utf-8') + b'\x00'


def sub(sig, payload):
    return sig + struct.pack('<H', len(payload)) + payload


def build_tes4(masters, nrec, nextid, signature):
    body = bytearray()
    body += sub(b'HEDR', struct.pack('<fII', 1.70, nrec, nextid))
    body += sub(b'CNAM', zstring('DEFAULT'))
    body += sub(b'SNAM', zstring(signature))
    for m in masters:
        body += sub(b'MAST', zstring(m))
        body += sub(b'DATA', b'\x00' * 8)
    return (b'TES4' + struct.pack('<I', len(body))
            + struct.pack('<I', 0)          # record flags
            + struct.pack('<I', 0)          # form id
            + struct.pack('<I', 0)          # version control info
            + struct.pack('<HH', 44, 0)     # form version + vcs2
            + bytes(body))


def build_record(sig, formid, subrecords):
    body = bytearray()
    for s, p in subrecords:
        body += sub(s, p)
    return (struct.pack('<4sIIIIHH', sig, len(body), 0, formid, 0, 44, 0)
            + bytes(body))


def build_grup(label: bytes, content: bytes, group_type=0):
    hdr = bytearray(b'GRUP')
    hdr += struct.pack('<I', 24 + len(content))
    hdr += label
    hdr += struct.pack('<i', group_type)
    hdr += b'\x00' * 8
    return bytes(hdr) + content


def masters_of(plugin):
    size = struct.unpack_from('<I', plugin, 4)[0]
    o, end, out = 24, 24 + size, []
    while o + 6 <= end:
        sig = plugin[o:o + 4]
        sl = struct.unpack_from('<H', plugin, o + 4)[0]
        o += 6
        if sig == b'MAST':
            out.append(plugin[o:o + sl].split(b'\x00')[0].decode())
        o += sl
    return out


def main():
    ss = read(SS)
    found = None
    for off, sig, size, fid in iter_records(ss):
        if fid == TARGET_FORMID:
            found = (off, sig, size, list(iter_subs(ss, off, size)))
    if not found:
        print('target not found'); return 1
    off, sig, size, subs = found

    print(f'target {sig.decode()} {TARGET_EDID} [{TARGET_FORMID:08X}]')
    print('subrecords:', ', '.join(f'{s.decode()}({l})' for s, _o, l in subs))

    known = existing_formids(ss)
    # object arrays may also point at vanilla records
    sky_path = SKYRIM_ESM
    if os.path.isfile(sky_path):
        known |= existing_formids(read(sky_path))
    print(f'known FormIDs for validation: {len(known)}')
    new_subs = []
    changed = False
    for s, so, sl in subs:
        payload = ss[so:so + sl]
        if s != b'VMAD':
            new_subs.append((s, payload))
            continue
        poff, old_count, fids = find_prop_count_offset(payload, TARGET_PROP, known)
        if poff is None:
            print(f'!! property {TARGET_PROP} could not be located')
            new_subs.append((s, payload))
            continue
        patched = bytearray(payload)
        struct.pack_into('<I', patched, poff, 0)
        print(f'\nVMAD {sl} bytes')
        print(f'  {TARGET_PROP}: count u32 at offset {poff}')
        print(f'    before = {old_count} object(s): '
              f'{", ".join(f"{f:08X}" for f in fids)}')
        print(f'    after  = 0 object(s)')
        rebuilt = bytes(patched[:poff + 4]) + bytes(patched[poff + 4 + old_count * 8:])
        print(f'  VMAD size {sl} -> {len(rebuilt)} bytes')
        new_subs.append((s, rebuilt))
        changed = True

    if not changed:
        print('nothing changed'); return 1

    masters = masters_of(ss)
    if 'Spellsiphon.esp' not in masters:
        masters.append('Spellsiphon.esp')
    signature = (f'Spellsiphon - No Woven Power Lightning v{PATCH_VERSION}: clears '
                 f'{TARGET_EDID}.kssc_playeffectduring.EffectsToPlay so the '
                 f'Woven Power stack visual (vanilla dragon-resurrection streaks) is '
                 f'never played. Sound and mechanics unchanged.')
    plugin = (build_tes4(masters, 1, TARGET_FORMID + 1, signature)
              + build_grup(b'MGEF', build_record(sig, TARGET_FORMID, new_subs)))

    out_dir = os.path.join(DIST, PLUGIN_NAME)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, PLUGIN_NAME + '.esp')
    with open(path, 'wb') as f:
        f.write(plugin)
    print(f'\nwritten -> {path} ({len(plugin):,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
