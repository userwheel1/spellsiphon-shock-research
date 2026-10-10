"""Full visual inventory of Spellsiphon.esp.

For every EFSH: textures, the visual parameters that control screen coverage,
and which MGEF / SPEL records reference it.  Records are sorted by a crude
"screen coverage" score so the worst offenders are obvious.
"""
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


def subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


def f32(data, name):
    off, _ = BY_NAME[name]
    return struct.unpack_from('<f', data, off)[0]


recs = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    recs.append({'off': off, 'sig': sig, 'size': size, 'fid': fid, 'edid': edid})

by_id = {r['fid']: r for r in recs}

# who references what
for r in recs:
    pat = struct.pack('<I', r['fid'])
    r['refs'] = []
    for other in recs:
        if other['fid'] == r['fid']:
            continue
        if pat in buf[other['off'] + 24:other['off'] + 24 + other['size']]:
            r['refs'].append(other)

rows = []
for r in recs:
    if r['sig'] != b'EFSH':
        continue
    tex, data = {}, None
    for st, d in subs(buf, r['off'], r['size']):
        n = st.decode()
        if n in ('ICON', 'ICO2', 'NAM7', 'NAM8', 'NAM9'):
            tex[n] = d.split(b'\x00')[0].decode('utf8', 'replace')
        elif n == 'DATA':
            data = d
    if data is None:
        continue
    fill = f32(data, 'Fill/Texture Effect - Presistent Alpha Ratio')
    fillfull = f32(data, 'Fill/Texture Effect - Full Alpha Ratio')
    edge = f32(data, 'Edge Effect - Persistent Alpha Ratio')
    edgefull = f32(data, 'Edge Effect - Full Alpha Ratio')
    cscale = f32(data, 'Color Scale')
    ck2a = f32(data, 'Color Key 2 - Color Alpha')
    score = (fill + edge) * ck2a * cscale
    rows.append({
        'edid': r['edid'], 'fid': r['fid'], 'tex': tex, 'score': score,
        'fill': fill, 'fillfull': fillfull, 'edge': edge, 'edgefull': edgefull,
        'cscale': cscale, 'ck2a': ck2a,
        'refs': [x for x in r['refs'] if x['sig'] in (b'MGEF', b'SPEL')],
    })

rows.sort(key=lambda x: -x['score'])

print(f"{'EFSH':<44}{'fill':>7}{'edge':>7}{'colSc':>7}{'score':>8}  applies-to")
print('-' * 120)
for r in rows:
    who = ', '.join(sorted({x['edid'] for x in r['refs']}))[:44]
    print(f"{r['edid'][:43]:<44}{r['fill']:>7.2f}{r['edge']:>7.2f}"
          f"{r['cscale']:>7.2f}{r['score']:>8.2f}  {who}")

print("\n\n=== EFSH records that use ShockParticles02.dds ===")
for r in rows:
    if 'ShockParticles02' in r['tex'].get('ICO2', ''):
        print(f"  {r['edid']:<42} score={r['score']:.2f}  "
              f"ICON={os.path.basename(r['tex'].get('ICON', '')) or '-'}  "
              f"NAM8={os.path.basename(r['tex'].get('NAM8', '')) or '-'}")
