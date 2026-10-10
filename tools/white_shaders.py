"""Inspect the shaders most likely responsible for a WHITE screen fill during
Woven Power stacking, and list every EFSH with its textures + key parameters.
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

CANDIDATES = [
    0x0474F355,  # KSSC_WhiteCracksShader
    0x04911CE5,  # KSSC_OverloadFX_Life_Shader
    0x0496CF20,  # KSSC_BoundSoulfoci_Shader
    0x04972025,  # KSSC_BoundSoulfoci_HitShader
    0x046E4E1B,  # KSSC_LifeCageShader
    0x044459F1,  # KSSC_ShockShader_Silent
    0x0403603E,  # KSSC_ShockShader (patched)
    0x040B4427,  # KSSC_WorldCircleEffectShader
    0x045ED051,  # KSSC_LifePullDisappearShader
]


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


def val(data, name):
    off, kind = BY_NAME[name]
    if kind == 'f32':
        return struct.unpack_from('<f', data, off)[0]
    if kind == 'u32':
        return struct.unpack_from('<I', data, off)[0]
    dw = struct.unpack_from('<I', data, off)[0]
    return (dw & 0xFF, (dw >> 8) & 0xFF, (dw >> 16) & 0xFF)


KEY = ['Fill/Texture Effect - Presistent Alpha Ratio',
       'Edge Effect - Persistent Alpha Ratio',
       'Color Key 1 - Color', 'Color Key 2 - Color', 'Color Key 3 - Color',
       'Color Key 1 - Color Alpha', 'Color Key 2 - Color Alpha',
       'Color Scale']

for off, sig, size, fid in records(buf):
    if sig != b'EFSH' or fid not in CANDIDATES:
        continue
    edid = tex = data = None
    tex = {}
    for st, d in subs(buf, off, size):
        if st == b'EDID':
            edid = d.split(b'\x00')[0].decode('utf8', 'replace')
        elif st in (b'ICON', b'ICO2', b'NAM7', b'NAM8', b'NAM9'):
            tex[st.decode()] = d.split(b'\x00')[0].decode('utf8', 'replace')
        elif st == b'DATA':
            data = d
    print(f"\n##### {edid}  [{fid:08X}]  DATA={len(data) if data else 0}B")
    print(f"   ICON={tex.get('ICON')!r}")
    print(f"   ICO2={tex.get('ICO2')!r}")
    print(f"   NAM7={tex.get('NAM7')!r}")
    print(f"   NAM8={tex.get('NAM8')!r}")
    print(f"   NAM9={tex.get('NAM9')!r}")
    if data:
        for k in KEY:
            if k in BY_NAME:
                print(f"   {k:<42} = {val(data, k)}")
