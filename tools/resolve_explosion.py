"""Resolve the Explosion that KSSC_WovenPowerVisualME plays, and find the Effect
Shader it uses.  This is the visual that stacks with Woven Power.
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
EXPL_FORMID = 0x040CEE0E
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


edid_of = {}
recs = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    edid_of[fid] = (sig.decode(), edid)
    recs.append((off, sig, size, fid, edid))


def show(fid, label):
    for off, sig, size, fid2, edid in recs:
        if fid2 != fid:
            continue
        print(f'\n===== {label}: {sig.decode()} {edid} [{fid:08X}] size={size}')
        for st, d in subs(buf, off, size):
            n = st.decode('ascii', 'replace')
            if n == 'EDID':
                continue
            if n in ('DATA', 'MODT', 'VMAD'):
                print(f'   {n:<5} ({len(d)} bytes)')
                continue
            if len(d) == 4:
                v = struct.unpack_from('<I', d, 0)[0]
                t = edid_of.get(v)
                if t:
                    print(f'   {n:<5} -> {t[0]} {v:08X}  {t[1]}')
                else:
                    fv = struct.unpack_from('<f', d, 0)[0]
                    print(f'   {n:<5} = {v} (0x{v:08X}) / {fv:g}')
            else:
                try:
                    print(f'   {n:<5} {d.split(bytes([0]))[0].decode("utf-8")!r}')
                except UnicodeDecodeError:
                    print(f'   {n:<5} ({len(d)}b) {d[:24].hex(" ")}')
        return True
    print(f'\n{label} [{fid:08X}] NOT FOUND in plugin')
    return False


# the explosion
show(EXPL_FORMID, 'Woven Power visual explosion')

print('\n=== which EFSH does that explosion use? ===')
for off, sig, size, fid2, edid in recs:
    if fid2 != EXPL_FORMID:
        continue
    for st, d in subs(buf, off, size):
        if st == b'DATA' and len(d) >= 4:
            # EXPL DATA: first dword = NAM9?; look for EFSH-ish refs in all subs
            pass
    # crude: print all 4-byte refs
    for st, d in subs(buf, off, size):
        if len(d) == 4:
            v = struct.unpack_from('<I', d, 0)[0]
            t = edid_of.get(v)
            if t and t[0] == 'EFSH':
                print(f'   EFSH via {st.decode()}: {v:08X} {t[1]}')
