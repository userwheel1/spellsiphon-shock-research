"""Exhaustive map of every visual SpellSiphon can apply to the PLAYER.

For each candidate effect this lists:
  * the script properties and the records they point at (spells, shaders,
    visual effects, art objects, explosions, sound)
  * whether the target is inside Spellsiphon.esp or vanilla

Goal: find the record that actually creates the flickering static around the
character while Woven Power accumulates - after shaders, textures and the
Woven Power effects-to-play array were all ruled out.
"""
from __future__ import annotations

import os
import struct
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

HERE = os.path.dirname(os.path.abspath(__file__))
SS = SPELLSIPHON_ESP
SKY = SKYRIM_ESM
SS_BUF = open(SS, 'rb').read()
SKY_BUF = open(SKY, 'rb').read()


def iter_records(b):
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


def iter_subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


def index(b):
    m = {}
    for off, sig, size, fid in iter_records(b):
        edid = None
        for st, d in iter_subs(b, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
        m[fid] = (sig.decode(), edid, off, size)
    return m


SSI = index(SS_BUF)
SKYI = index(SKY_BUF)


def label(fid):
    t = SSI.get(fid)
    if t:
        return f'{t[0]} {t[1]} [{fid:08X}]'
    t = SKYI.get(fid)
    if t:
        return f'{t[0]} {t[1]} [{fid:08X}] (vanilla)'
    return f'0x{fid:08X} (external)'


def sub_list(b, fid):
    t = SSI.get(fid) or SKYI.get(fid)
    if not t:
        return None, None
    sig, edid, off, size = t
    return (sig, edid), list(iter_subs(b, off, size))


# ------------------------------------------------------------------ VMAD read
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


def obj8(raw, at):
    """FormID is the second dword (verified against real bytes)."""
    return struct.unpack_from('<I', raw, at + 4)[0]


def walk_vmad(vmad):
    """Yield (scriptname, propname, type, value)."""
    r = R(vmad)
    r.u16(); r.u16(); n = r.u16()
    out = []
    for _ in range(n):
        try:
            sname = r.wstr(); r.u8(); nprops = r.u16()
        except Exception:
            break
        for _ in range(nprops):
            try:
                pn = r.wstr(); pt = r.u8(); r.u8()
            except Exception:
                return out
            try:
                if pt in (1, 6, 11):
                    cnt = r.u32()
                    vals = [obj8(vmad, r.i + k * 8) for k in range(cnt)]
                    r.i += cnt * 8
                    out.append((sname, pn, pt, vals))
                elif pt == 2:
                    out.append((sname, pn, pt, r.wstr()))
                elif pt == 3:
                    out.append((sname, pn, pt, r.i32()))
                elif pt == 4:
                    out.append((sname, pn, pt, r.f32()))
                elif pt == 5:
                    out.append((sname, pn, pt, r.u8()))
                elif pt == 0:
                    out.append((sname, pn, pt, None))
                elif pt == 12:
                    c = r.u32(); out.append((sname, pn, pt, [r.wstr() for _ in range(c)]))
                elif pt == 13:
                    c = r.u32(); out.append((sname, pn, pt, [r.i32() for _ in range(c)]))
                elif pt == 14:
                    c = r.u32(); out.append((sname, pn, pt, [r.f32() for _ in range(c)]))
                elif pt == 15:
                    c = r.u32(); out.append((sname, pn, pt, [r.u8() for _ in range(c)]))
                else:
                    return out
            except Exception:
                return out
    return out


VISUAL_PROP_HINT = ('shader', 'fx', 'effect', 'explosion', 'art', 'vfx', 'visual',
                    'imod', 'sound', 'spell', 'hazard', 'proj', 'node', 'attach')

TARGETS = [
    0x042B4A2C,   # KSSC_WovenPowerVisualME
    0x04094141,   # KSSC_WovenPowerME
    0x042B4A25,   # KSSC_WovenPowerDisplayME
    0x042B4A28,   # KSSC_WovenPowerContactME
    0x04427E9E,   # KSSC_Attunement_WorldME
    0x04427E9F,   # KSSC_Attunement_LifeME
    0x04427EA0,   # KSSC_Attunement_DeathME
    0x04001829,   # KSSC_CastTrackingME
]

print('=' * 100)
print('EVERY VISUAL SPELLSIPHON CAN APPLY TO THE PLAYER')
print('=' * 100)

for fid in TARGETS:
    t = SSI.get(fid)
    if not t:
        print(f'\n### {fid:08X} not found')
        continue
    sig, edid, off, size = t
    print(f'\n### {sig} {edid} [{fid:08X}]')
    for st, d in iter_subs(SS_BUF, off, size):
        n = st.decode('ascii', 'replace')
        if n == 'VMAD':
            props = walk_vmad(d)
            for sname, pn, pt, val in props:
                low = pn.lower()
                if not any(h in low for h in VISUAL_PROP_HINT):
                    continue
                if isinstance(val, list):
                    for v in val:
                        print(f'    {sname}.{pn} -> {label(v)}')
                    if not val:
                        print(f'    {sname}.{pn} = [] (empty)')
                else:
                    print(f'    {sname}.{pn} = {val!r}')
        elif n in ('EFID', 'EFIT'):
            continue
        elif len(d) == 4:
            v = struct.unpack_from('<I', d, 0)[0]
            t2 = SSI.get(v) or SKYI.get(v)
            if t2 and t2[0] in ('EFSH', 'SPEL', 'EXPL', 'RFCT', 'ARTO', 'HAZD',
                                'PROJ', 'IMAD', 'LIGH', 'STAT', 'SNDR', 'DUAL'):
                print(f'    [{n}] -> {label(v)}')

print('\n' + '=' * 100)
print('ALL EFFECT SHADERS REFERENCED BY ANY SPELLSIPHON VMAD OBJECT PROPERTY')
print('=' * 100)
seen = set()
for fid, (sig, edid, off, size) in sorted(SSI.items()):
    for st, d in iter_subs(SS_BUF, off, size):
        if st != b'VMAD':
            continue
        for sname, pn, pt, val in walk_vmad(d):
            vals = val if isinstance(val, list) else ([val] if isinstance(val, int) else [])
            for v in vals:
                t2 = SSI.get(v)
                if t2 and t2[0] == 'EFSH':
                    key = (fid, v)
                    if key in seen:
                        continue
                    seen.add(key)
                    print(f'  {sig} {edid} [{fid:08X}].{pn} -> EFSH {t2[1]} [{v:08X}]')
print(f'\ntotal distinct (record, shader) links: {len(seen)}')
