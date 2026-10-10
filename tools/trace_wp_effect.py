"""Find every record that references the raw 8-byte object value seen in
KSSC_WovenPowerVisualME's EffectsToPlay array, then walk the chain further.

Searches the literal byte pattern so it works regardless of how the 8-byte
object reference is laid out.
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

# raw 8 bytes from EffectsToPlay in KSSC_WovenPowerVisualME
PATTERN = bytes.fromhex('0000ffff0eee0c00')

# candidate FormIDs implied by that value
CANDIDATES = [0x0CEE0000, 0x0CEE0EEE, 0x0CEEEE0C, 0x00000CEE, 0x0CEE0000 | 0xEE]


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


def subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


recs = []
by_id = {}
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    recs.append((off, sig, size, fid, edid))
    by_id[fid] = (sig.decode(), edid)

print("records whose own FormID matches a candidate decoding:")
for c in CANDIDATES:
    t = by_id.get(c)
    if t:
        print(f"   {c:08X} -> {t[0]} {t[1]}")

print("\nrecords containing the literal byte pattern "
      f"{PATTERN.hex(' ')}:")
for off, sig, size, fid, edid in recs:
    body = buf[off + 24:off + 24 + size]
    if PATTERN in body:
        print(f"   {sig.decode():<5} {fid:08X}  {edid}")

print("\nall records that reference KSSC_ShockShader (0403603E):")
for off, sig, size, fid, edid in recs:
    body = buf[off + 24:off + 24 + size]
    if struct.pack('<I', 0x0403603E) in body:
        print(f"   {sig.decode():<5} {fid:08X}  {edid}")

# Also: what do the Woven Power spells cast? Inspect KSSC_WovenPowerVisualME's
# spell/script siblings via SPEL records that reference it.
print("\nrecords referencing KSSC_WovenPowerVisualME (042B4A2C):")
for off, sig, size, fid, edid in recs:
    body = buf[off + 24:off + 24 + size]
    if struct.pack('<I', 0x042B4A2C) in body:
        print(f"   {sig.decode():<5} {fid:08X}  {edid}")
