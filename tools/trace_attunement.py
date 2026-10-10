"""Follow the FXDragonResurStreaks chain and inspect the Attunement shaders -
the visuals that stay applied while the player is attuned to Life.
"""
import struct
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)
SS = SPELLSIPHON_ESP
SKY = SKYRIM_ESM
def load(p):
    with open(p, 'rb') as f:
        return f.read()


BUF = {'ss': load(SS), 'sky': load(SKY)}


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


IDX = {}
for tag, b in BUF.items():
    m = {}
    for off, sig, size, fid in records(b):
        edid = None
        for st, d in subs(b, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
        m[fid] = (sig.decode(), edid, off, size, tag)
    IDX[tag] = m


def find(fid):
    for tag in ('ss', 'sky'):
        if fid in IDX[tag]:
            return IDX[tag][fid]
    return None


def label(fid):
    t = find(fid)
    return f'{t[0]} {t[1]} [{fid:08X}]' if t else f'0x{fid:08X} (not found)'


print('=== following the FXDragonResurStreaks chain (vanilla) ===')
cur = 0x000CEE0E
seen = set()
for _ in range(6):
    if cur in seen or cur == 0:
        break
    seen.add(cur)
    t = find(cur)
    if not t:
        print(f'  {cur:08X} -> not found'); break
    sig, edid, off, size, tag = t
    b = BUF[tag]
    print(f'\n  {sig} {edid} [{cur:08X}]  ({tag})')
    nxt = None
    for st, d in subs(b, off, size):
        n = st.decode('ascii', 'replace')
        if n in ('EDID', 'MODT', 'OBND'):
            continue
        if len(d) == 4:
            v = struct.unpack_from('<I', d, 0)[0]
            if v:
                print(f'      {n:<5} -> {label(v)}')
                if n in ('DATA', 'NAM1', 'NAM2', 'NAM3', 'NAM4'):
                    nxt = v
        elif len(d) == 12 and n == 'DATA':
            v = struct.unpack_from('<I', d, 0)[0]
            print(f'      DATA  first ref -> {label(v)}')
            nxt = v
        elif len(d) <= 40:
            try:
                s = d.split(b'\x00')[0].decode('utf-8')
                if s and all(32 <= ord(c) < 127 for c in s) and len(s) > 2:
                    print(f'      {n:<5} {s!r}')
                    continue
            except UnicodeDecodeError:
                pass
            print(f'      {n:<5} ({len(d)}b) {d[:24].hex(" ")}')
    cur = nxt or 0

print('\n\n=== Attunement shaders (persist while attuned to Life) ===')
for fid, (sig, edid, off, size, tag) in sorted(IDX['ss'].items()):
    if sig == 'EFSH' and edid and ('Attunement' in edid or 'BoundWeaponAttunement' in edid or 'WeaponEnchantment' in edid or 'Soulfoci' in edid):
        b = BUF[tag]
        tex, data = {}, None
        for st, d in subs(b, off, size):
            n = st.decode()
            if n in ('ICON', 'ICO2', 'NAM7', 'NAM8', 'NAM9'):
                tex[n] = d.split(b'\x00')[0].decode('utf8', 'replace')
            elif n == 'DATA':
                data = d
        import os as _os
        key1 = _os.path.basename(tex.get('ICON', '')) or '-'
        key2 = _os.path.basename(tex.get('ICO2', '')) or '-'
        key8 = _os.path.basename(tex.get('NAM8', '')) or '-'
        cs = struct.unpack_from('<f', data, 344)[0] if data and len(data) > 348 else 0
        print(f'  {edid:<42} [{fid:08X}]  ICON={key1:<20} ICO2={key2:<22} NAM8={key8:<28} colScale={cs:.2f}')
