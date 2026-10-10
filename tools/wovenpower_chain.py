"""Dump the Woven Power / attunement chain to find which shader draws the
on-character electrification while Woven Power stacks accumulate.

Prints, for every relevant record:
  * its script + the Effect Shader / Spell properties it references
  * the MGEF DATA archetype / magnitude / duration fields
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

WANT = {
    'KSSC_WovenPowerME', 'KSSC_WovenPowerVisualME', 'KSSC_WovenPowerDisplayME',
    'KSSC_WovenPowerContactME', 'kssc_elementcomboME',
    'KSSC_Attunement_WorldME', 'KSSC_Attunement_LifeME', 'KSSC_Attunement_DeathME',
    'KSSC_CastTrackingME',
}


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


def subs(b, rec_off, size):
    o, end = rec_off + 24, rec_off + 24 + size
    while o + 6 <= end:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


class R:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v

    def u16(self):
        v = struct.unpack_from('<H', self.b, self.o)[0]; self.o += 2; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.o)[0]; self.o += 4; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.o)[0]; self.o += 4; return v

    def f32(self):
        v = struct.unpack_from('<f', self.b, self.o)[0]; self.o += 4; return v

    def wstr(self):
        n = self.u16(); s = self.b[self.o:self.o + n].decode('utf8', 'replace')
        self.o += n
        return s


def read_obj(r):
    """VMAD object reference: first dword of the 8-byte value is the FormID."""
    fid = r.u32(); r.u32(); return fid


def read_val(r):
    """VMAD property value. Object-array types are 1, 6 and 11."""
    t = r.u8()
    if t in (1, 6, 11):
        n = r.u32()
        return [read_obj(r) for _ in range(n)]
    if t == 2: return r.wstr()
    if t == 3: return r.i32()
    if t == 4: return round(r.f32(), 4)
    if t == 5: return bool(r.u8())
    if t == 12: return [r.wstr() for _ in range(r.u32())]
    if t == 13: return [r.i32() for _ in range(r.u32())]
    if t == 14: return [round(r.f32(), 4) for _ in range(r.u32())]
    if t == 15: return [r.u8() for _ in range(r.u32())]
    if t == 0: return None
    raise ValueError(t)


def parse_vmad(raw):
    r = R(raw, 0)
    end = len(raw)
    r.u16(); r.u16()
    n = r.u16()
    out = []
    for _ in range(n):
        if r.o >= end:
            break
        try:
            name = r.wstr(); r.u8(); np = r.u16()
        except Exception as e:
            out.append((f'<header stopped: {e}>', []))
            break
        if np > 400:
            out.append((name, [('<implausible prop count>', -1, None)]))
            break
        props = []
        for _ in range(np):
            if r.o >= end:
                props.append(('<truncated>', -1, None)); break
            try:
                pn = r.wstr(); pt = r.u8(); r.u8(); pv = read_val(r)
            except Exception as e:
                props.append((f'<stopped {e}>', -1, None)); break
            props.append((pn, pt, pv))
        out.append((name, props))
    return out


# EDID map
edid_of = {}
recs = []
for off, sig, size, fid in records(buf):
    edid = None
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
    edid_of[fid] = edid
    recs.append((off, sig, size, fid, edid))

print("=== Woven Power / attunement chain ===\n")
for off, sig, size, fid, edid in recs:
    if edid not in WANT:
        continue
    print(f"----- {sig.decode()} {edid}  [{fid:08X}]  size={size}")
    for st, d in subs(buf, off, size):
        if st == b'DATA' and len(d) >= 8:
            arch = d[0]
            mag = struct.unpack_from('<f', d, 4)[0]
            print(f"    DATA: archetype_byte={arch}  magnitude={mag:g}  len={len(d)}")
        elif st == b'VMAD':
            for sname, props in parse_vmad(d):
                refs = []
                for p, t, v in props:
                    if isinstance(v, list) and v and isinstance(v[0], int):
                        refs.append((p, v))
                    elif isinstance(v, int) and t in (1, 6, 11):
                        refs.append((p, [v]))
                print(f"    script {sname}: {len(props)} props, {len(refs)} ref prop(s)")
                for p, vals in refs:
                    for x in vals:
                        print(f"        {p:<34} -> {edid_of.get(x, '?'):<32} [{x:08X}]")
        elif st in (b'FULL', b'EDID'):
            continue
    print()
