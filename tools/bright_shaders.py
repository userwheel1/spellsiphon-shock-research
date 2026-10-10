"""List every EFSH that contributes to the bright "Life" look:
bright gradient, shock particles, shock tile, or a high colour scale."""
import struct, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from efsh_layout import BY_NAME  # noqa: E402
import sys
import os

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)
SS = SPELLSIPHON_ESP
b = open(PLUGIN, 'rb').read()


def recs(buf):
    o, n = 0, len(buf)
    while o + 24 <= n:
        s = buf[o:o + 4]
        sz = struct.unpack_from('<I', buf, o + 4)[0]
        if s == b'GRUP':
            o += 24
            continue
        if o + 24 + sz > n:
            break
        yield o, s, sz, struct.unpack_from('<I', buf, o + 12)[0]
        o += 24 + sz


def subs(buf, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = buf[o:o + 4]
        sl = struct.unpack_from('<H', buf, o + 4)[0]
        o += 6
        yield st, buf[o:o + sl]
        o += sl


rows = []
for o, s, sz, fid in recs(b):
    if s != b'EFSH':
        continue
    edid = None
    tex, data = {}, None
    for st, d in subs(b, o, sz):
        n = st.decode()
        if n == 'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace')
        elif n in ('ICON', 'ICO2', 'NAM7', 'NAM8', 'NAM9'):
            tex[n] = d.split(b'\x00')[0].decode('utf8', 'replace')
        elif n == 'DATA':
            data = d
    if not edid or data is None:
        continue
    off, _ = BY_NAME['Color Scale']
    cs = struct.unpack_from('<f', data, off)[0]
    icon = os.path.basename(tex.get('ICON', '')) or '-'
    ico2 = os.path.basename(tex.get('ICO2', '')) or '-'
    nam8 = os.path.basename(tex.get('NAM8', '')) or '-'
    rows.append((edid, fid, icon, ico2, nam8, cs))

bright = [r for r in rows
          if 'GradShockHit' in r[4] or 'ShockParticles02' in r[3]
          or 'ShockTile01' in r[2] or r[5] >= 2.0]

print(f"{'EFSH':<44}{'ICON':<22}{'ICO2':<26}{'NAM8':<30}{'colScale':>8}")
print('-' * 132)
for edid, fid, icon, ico2, nam8, cs in sorted(bright, key=lambda x: -x[5]):
    print(f"{edid[:43]:<44}{icon:<22}{ico2:<26}{nam8:<30}{cs:>8.2f}")

print(f"\ntotal EFSH in plugin: {len(rows)}")
print(f"bright 'Life' shaders: {len(bright)}")
print("\nFormIDs for patching:")
for edid, fid, *_ in sorted(bright, key=lambda x: -x[5]):
    print(f"    0x{fid:08X},   # {edid}")
