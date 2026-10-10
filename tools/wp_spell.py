"""Show the KSSC_WovenPower spell record in full, plus every SPEL that references
the Woven Power magic effects, so we can see which visuals attach to stacking."""
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

WP_ME = {0x04094141: 'KSSC_WovenPowerME',
         0x042B4A25: 'KSSC_WovenPowerDisplayME',
         0x042B4A28: 'KSSC_WovenPowerContactME',
         0x042B4A2C: 'KSSC_WovenPowerVisualME'}
WP_SPEL = 0x04078D9A


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


edid_of = {}
recs = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    edid_of[fid] = (sig.decode(), edid)
    recs.append((off, sig, size, fid, edid))


def dump_spel(fid_want):
    for off, sig, size, fid, edid in recs:
        if fid != fid_want:
            continue
        print(f"\n===== SPEL {edid} [{fid:08X}] size={size}")
        for st, d in subs(buf, off, size):
            n = st.decode('ascii', 'replace')
            if n == 'EDID':
                print(f"   EDID  {d.split(bytes([0]))[0].decode()}")
            elif n == 'FULL':
                print(f"   FULL  {d.split(bytes([0]))[0].decode()}")
            elif n in ('SPIT', 'DATA'):
                if len(d) >= 8:
                    cost, flags = struct.unpack_from('<II', d, 0)
                    print(f"   {n:<5} cost={cost} flags=0x{flags:08X}")
                else:
                    print(f"   {n:<5} {d.hex(' ')}")
            elif n == 'OBND':
                continue
            elif len(d) == 4:
                v = struct.unpack_from('<I', d, 0)[0]
                s2, e2 = edid_of.get(v, ('?', '(external)'))
                print(f"   {n:<5} -> {s2:<5} {v:08X}  {e2}")
            elif len(d) == 8:
                v1, v2 = struct.unpack_from('<II', d, 0)
                for v in (v1, v2):
                    s2, e2 = edid_of.get(v, ('?', '(external)'))
                    print(f"   {n:<5} -> {s2:<5} {v:08X}  {e2}")
            else:
                try:
                    print(f"   {n:<5} {d.split(bytes([0]))[0].decode()!r}")
                except UnicodeDecodeError:
                    print(f"   {n:<5} ({len(d)}b) {d[:16].hex(' ')}")


dump_spel(WP_SPEL)

print("\n\n=== SPEL records that reference any Woven Power magic effect ===")
for off, sig, size, fid, edid in recs:
    if sig != b'SPEL':
        continue
    body = buf[off + 24:off + 24 + size]
    hits = [name for mf, name in WP_ME.items()
            if struct.pack('<I', mf) in body]
    if hits:
        print(f"   SPEL {fid:08X}  {edid}   uses: {', '.join(hits)}")
