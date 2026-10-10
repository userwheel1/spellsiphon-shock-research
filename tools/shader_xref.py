"""Find every record in Spellsiphon.esp that references a given Effect Shader,
resolving both VMAD script properties and raw FormID mentions.

Also dumps the MGEF DATA duration fields for the attunement / Woven Power
effects so we can explain how long a visual can persist.
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
SUSPECTS = {
    0x0403603E: 'KSSC_ShockShader          (the one we patched)',
    0x044459F1: 'KSSC_ShockShader_Silent',
    0x04168F4D: 'KSSC_FlameEffect',
    0x043015E5: 'KSSC_DrawDeathShader',
    0x04167F4D: 'KSSC_DrawDeathShader? (alt)',
}

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


# Build EDID map
edid_of = {}
records_list = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace')
            break
    edid_of[fid] = edid
    records_list.append((off, sig, size, fid, edid))

print("=== records that mention each suspect shader FormID ===")
for fid_target, label in SUSPECTS.items():
    pattern = struct.pack('<I', fid_target)
    hits = []
    for off, sig, size, fid, edid in records_list:
        body = buf[off + 24:off + 24 + size]
        if pattern in body:
            hits.append((sig.decode(), fid, edid))
    print(f"\n-- {label}  ({fid_target:08X}) : {len(hits)} reference(s)")
    for sig, fid, edid in hits:
        print(f"     {sig:<5} {fid:08X}  {edid}")
