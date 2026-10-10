"""Find EVERY record in Spellsiphon.esp that plays a visual effect through the
kssc_playeffectduring script, and every record that references the vanilla
dragon-resurrection streaks effect used by Woven Power.

This identifies the record that actually CREATES the lightning around the
player, so it can be replaced rather than dimmed.
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
STREAKS = 0x000CEE0E          # RFCT FXDragonResurStreaksEffect

buf = open(SS, 'rb').read()
sky = open(SKY, 'rb').read()


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


def props_of(vmad):
    """Return list of (script, propname, type, value-ish)."""
    r = R(vmad)
    r.u16(); r.u16(); n = r.u16()
    out = []
    for _ in range(n):
        sname = r.wstr(); r.u8(); nprops = r.u16()
        for _ in range(nprops):
            pn = r.wstr(); pt = r.u8(); r.u8()
            if pt in (1, 6, 11):
                cnt = r.u32()
                vals = []
                for _ in range(cnt):
                    fid = r.u32(); r.u32()
                    vals.append(fid)
                out.append((sname, pn, 'ObjectArray', vals))
            elif pt == 2:
                out.append((sname, pn, 'String', r.wstr()))
            elif pt == 3:
                out.append((sname, pn, 'Int', r.i32()))
            elif pt == 4:
                out.append((sname, pn, 'Float', r.f32()))
            elif pt == 5:
                out.append((sname, pn, 'Bool', r.u8()))
            elif pt == 0:
                r.u8()
                out.append((sname, pn, 'None', None))
            elif pt == 12:
                c = r.u32(); out.append((sname, pn, 'StringArray', [r.wstr() for _ in range(c)]))
            elif pt == 13:
                c = r.u32(); out.append((sname, pn, 'IntArray', [r.i32() for _ in range(c)]))
            elif pt == 14:
                c = r.u32(); out.append((sname, pn, 'FloatArray', [r.f32() for _ in range(c)]))
            elif pt == 15:
                c = r.u32(); out.append((sname, pn, 'BoolArray', [r.u8() for _ in range(c)]))
            else:
                raise ValueError(pt)
    return out


edid_of = {}
recs = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    edid_of[fid] = (sig.decode(), edid)
    recs.append((off, sig, size, fid, edid))

# name map for skyrim too (for reporting the streaks target)
sky_names = {}
for off, sig, size, fid in records(sky):
    if fid in (0x000CEE0E, 0x000CEE0D, 0x000CEE0C):
        edid = None
        for st, d in subs(sky, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
        sky_names[fid] = (sig.decode(), edid)

print('=== records whose scripts play a visual effect (kssc_playeffectduring) ===')
print(f'    target RFCT FXDragonResurStreaksEffect = 0x{STREAKS:08X}\n')
for off, sig, size, fid, edid in recs:
    for st, d in subs(buf, off, size):
        if st != b'VMAD':
            continue
        try:
            props = props_of(d)
        except Exception:
            continue
        for sname, pn, pt, val in props:
            if pn in ('EffectsToPlay', 'IntroFX', 'OutroFX', 'LoopFX',
                      'StaticFX', 'ExplosionToPlace', 'EffectsToApply',
                      'ShaderToApply', 'TargetShader', 'InitialShader',
                      'PersistentShader', 'RebuildVFX', 'DismissFX'):
                mark = ''
                if isinstance(val, list) and STREAKS in val:
                    mark = '   <=== DRAGON STREAKS (lightning!)'
                print(f'  {sig.decode():<5} {fid:08X} {str(edid):<34} '
                      f'{sname}.{pn} = {val}{mark}')

print('\n=== records that reference the streaks RFCT by FormID ===')
pat = struct.pack('<I', STREAKS)
for off, sig, size, fid, edid in recs:
    if pat in buf[off + 24:off + 24 + size]:
        print(f'  {sig.decode():<5} {fid:08X}  {edid}')

print('\n=== vanilla identity of the streaks chain ===')
for fid, t in sorted(sky_names.items()):
    print(f'  {fid:08X}  {t[0]}  {t[1]}')
