"""Correctly parse the VMAD of KSSC_WovenPowerVisualME.

The object-value layout that works for this file was pinned empirically:
for the 8 bytes  f1 22 00 04 | 14 00 ...  the FormID is 0x040022F1, i.e.
    object = (dword0 >> 16) | (dword1 << 16) & 0xFFFFFFFF
with dword0 = 0x040022F1 and dword1 = 0x00000014 in that example.

Rather than guess, this script BRUTE-FORCES the decode: it walks the VMAD with
all three candidate layouts and reports which one yields FormIDs that actually
exist in the plugin.
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
TARGET = 'KSSC_WovenPowerVisualME'
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

vmad = None
for off, sig, size, fid, edid in recs:
    if edid == TARGET:
        for st, d in subs(buf, off, size):
            if st == b'VMAD':
                vmad = d

if vmad is None:
    print('VMAD not found')
    sys.exit(1)

print(f'VMAD of {TARGET}: {len(vmad)} bytes\n')


class R:
    def __init__(self, b):
        self.b, self.i = b, 0

    def u8(self):
        v = self.b[self.i]; self.i += 1; return v

    def u16(self):
        v = struct.unpack_from('<H', self.b, self.i)[0]; self.i += 2; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.i)[0]; self.i += 4; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.i)[0]; self.i += 4; return v

    def f32(self):
        v = struct.unpack_from('<f', self.b, self.i)[0]; self.i += 4; return v

    def wstr(self):
        n = self.u16()
        s = self.b[self.i:self.i + n].decode('utf8', 'replace'); self.i += n
        return s


def layout_a(a, b):
    """dword0's low 16 bits + dword1's low 16 bits (the original guess)."""
    return (a & 0xFFFF) | ((b & 0xFFFF) << 16)


def layout_b(a, b):
    """first dword is the whole FormID."""
    return a


def layout_c(a, b):
    """second dword is the whole FormID."""
    return b


for name, fn in (('A: (d0&FFFF)|(d1&FFFF)<<16', layout_a),
                 ('B: d0', layout_b),
                 ('C: d1', layout_c)):
    r = R(vmad)
    r.u16(); r.u16(); n = r.u16()
    valid = 0
    total = 0
    samples = []
    try:
        for _ in range(n):
            sname = r.wstr(); r.u8(); nprops = r.u16()
            for _ in range(nprops):
                pn = r.wstr(); pt = r.u8(); pf = r.u8()
                if pt in (1, 6, 11):
                    cnt = r.u32()
                    for _ in range(cnt):
                        d0 = r.u32(); d1 = r.u32()
                        total += 1
                        fid = fn(d0, d1) & 0xFFFFFFFF
                        if fid in edid_of:
                            valid += 1
                            samples.append((sname, pn, fid, edid_of[fid]))
                        # keep the per-property ending sane
                    # end object array
                elif pt == 2:
                    r.wstr()
                elif pt == 3:
                    r.u32()
                elif pt == 4:
                    r.f32()
                elif pt == 5:
                    r.u8()
                elif pt == 0:
                    pass
                elif pt == 12:
                    for _ in range(r.u32()):
                        r.wstr()
                elif pt == 13:
                    for _ in range(r.u32()):
                        r.u32()
                elif pt == 14:
                    for _ in range(r.u32()):
                        r.f32()
                elif pt == 15:
                    for _ in range(r.u32()):
                        r.u8()
                else:
                    raise ValueError(f'unknown type {pt}')
    except Exception as ex:
        pass
    print(f'layout {name:<28} object refs parsed={total:<3} resolvable={valid}')
    for sname, pn, fid, tgt in samples:
        print(f'      script {sname}  {pn}  -> {tgt[0]} {fid:08X} {tgt[1]}')
    print()
