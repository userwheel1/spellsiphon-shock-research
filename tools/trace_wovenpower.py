"""Trace the actual Woven Power visual chain.

Verified from xEdit's decode of KSSC_WovenPowerVisualME:
    kssc_playeffectduring.EffectsToPlay = RFCT 000CEE0E <FXDragonResurStreaksEffect>
    kssc_explosionattarget.ExplosionToPlace = EXPL 04504369 <KSSC_WovenPowerExplosion>

This dumps both records and resolves every effect-shader they reference, in both
Spellsiphon.esp and Skyrim.esm.
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
SKY = SKYRIM_ESM
WANT = [
    (SS, 0x04504369, 'KSSC_WovenPowerExplosion'),
    (SS, 0x042B4A2C, 'KSSC_WovenPowerVisualME'),
    (SKY, 0x000CEE0E, 'FXDragonResurStreaksEffect (RFCT, vanilla)'),
]


def load(p):
    with open(p, 'rb') as f:
        return f.read()


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


index = {}
for path, tag in ((SS, 'ss'), (SKY, 'sky')):
    b = load(path)
    m = {}
    for off, sig, size, fid in records(b):
        edid = None
        for st, d in subs(b, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
        m[fid] = (sig.decode(), edid, off, size, b)
    index[tag] = m
    if tag == 'ss':
        SS_BUF = b
    else:
        SKY_BUF = b


def name_of(fid):
    for tag in ('ss', 'sky'):
        t = index[tag].get(fid)
        if t:
            return f'{t[0]} {t[1]}'
    return None


for path, fid, label in WANT:
    tag = 'ss' if path == SS else 'sky'
    t = index[tag].get(fid)
    if not t:
        print(f'\n### {label} [{fid:08X}] NOT FOUND')
        continue
    sig, edid, off, size, b = t
    print(f'\n### {sig} {edid} [{fid:08X}]  size={size}')
    for st, d in subs(b, off, size):
        n = st.decode('ascii', 'replace')
        if n == 'EDID':
            continue
        if n in ('VMAD', 'MODT'):
            print(f'   {n:<5} ({len(d)} bytes)')
            continue
        if len(d) == 4:
            v = struct.unpack_from('<I', d, 0)[0]
            nm = name_of(v)
            if nm:
                print(f'   {n:<5} -> {nm}  [{v:08X}]')
            else:
                print(f'   {n:<5} = 0x{v:08X}')
        elif len(d) == 8 and n == 'DATA':
            print(f'   {n:<5} {d.hex(" ")}')
        else:
            try:
                s = d.split(b'\x00')[0].decode('utf-8')
                if s and all(32 <= ord(c) < 127 for c in s):
                    print(f'   {n:<5} {s!r}')
                else:
                    print(f'   {n:<5} ({len(d)}b) {d[:28].hex(" ")}')
            except UnicodeDecodeError:
                print(f'   {n:<5} ({len(d)}b) {d[:28].hex(" ")}')


# which EFSH does the explosion reference?
print('\n\n=== effect shaders referenced by KSSC_WovenPowerExplosion ===')
t = index['ss'].get(0x04504369)
if t:
    sig, edid, off, size, b = t
    for st, d in subs(b, off, size):
        if st == b'DATA' and len(d) >= 4:
            pass
    # search the whole record for any EFSH formid
    body = b[off + 24:off + 24 + size]
    for fid2, (sig2, edid2, _o, _s, _b) in index['ss'].items():
        if sig2 == 'EFSH' and struct.pack('<I', fid2) in body:
            print(f'   EFSH {edid2} [{fid2:08X}]')
