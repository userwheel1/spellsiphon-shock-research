"""Definitive cross-reference: for every EFSH in Spellsiphon.esp, list the records
that reference it (raw FormID byte scan, no VMAD parsing).

This answers "which shader draws what" without depending on a script parser.
"""
import struct
import sys
import os

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)
SS = SPELLSIPHON_ESP
buf = open(PLUGIN, 'rb').read()


def records(b):
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


def subs(b, rec_off, size):
    o, end = rec_off + 24, rec_off + 24 + size
    while o + 6 <= end:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


recs = []
efsh = {}
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace')
            break
    recs.append((off, sig, size, fid, edid))
    if sig == b'EFSH':
        efsh[fid] = edid

print(f"EFSH records in plugin: {len(efsh)}\n")

# index records by their own FormID for readable output
for target, tname in sorted(efsh.items()):
    refs = []
    pat = struct.pack('<I', target)
    for off, sig, size, fid, edid in recs:
        if fid == target:
            continue
        body = buf[off + 24:off + 24 + size]
        if pat in body:
            refs.append((sig.decode('ascii'), fid, edid))
    if not refs:
        continue
    print(f"EFSH {tname}  [{target:08X}]  <- {len(refs)} ref(s)")
    for sig, fid, edid in sorted(refs):
        print(f"      {sig:<5} {fid:08X}  {edid}")
    print()
