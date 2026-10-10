"""Validate tools/efsh_layout.py against the xDump-decoded reference values.

For each field in LAYOUT, read the value from the record's raw DATA payload and
compare it with the value xDump printed.  Any mismatch means the offset is wrong.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from efsh_layout import LAYOUT, BY_NAME  # noqa: E402

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

RESEARCH = os.path.join(os.path.dirname(PROJECT), 'research')

# Expected values transcribed from the xDump output.
# (reference file, label, formID, dict of field-name -> expected value)
EXPECTED_MOD = {
    'Membrane Shader - Specular Color': (0, 0, 0),
    'Membrane Shader - Specular Strength': 5,
    'Membrane Shader - Specular Color Scale': 1,
    'Membrane Shader - Unknown12': 3,
    'Fill/Texture Effect - Color Key 1': (0, 0, 0),
    'Fill/Texture Effect - Alpha Fade In Time': 0.2,
    'Fill/Texture Effect - Full Alpha Time': 0.05,
    'Fill/Texture Effect - Alpha Fade Out Time': 0.75,
    'Fill/Texture Effect - Presistent Alpha Ratio': 0.16,
    'Fill/Texture Effect - Alpha Pulse Frequency': 1.0,
    'Fill/Texture Effect - Texture Animation Speed (U)': 0.9,
    'Fill/Texture Effect - Texture Animation Speed (V)': 0.5,
    'Edge Effect - Fall Off': 1.75,
    'Edge Effect - Color': (255, 255, 255),
    'Edge Effect - Persistent Alpha Ratio': 1.0,
    'Fill/Texture Effect - Full Alpha Ratio': 0.222,
    'Edge Effect - Full Alpha Ratio': 1.2,
    'Particle Shader - Particle Birth Ramp Up Time': 0.2,
    'Particle Shader - Full Particle Birth Time': 0.05,
    'Particle Shader - Particle Birth Ramp Down Time': 0.75,
    'Particle Shader - Full Particle Birth Ratio': 22.0,
    'Particle Shader - Persistant Particle Count': 12.0,
    'Particle Shader - Particle Lifetime': 0.075,
    'Particle Shader - Particle Lifetime +/-': 0.02,
    'Particle Shader - Initial Speed Along Normal': 30.0,
    'Particle Shader - Acceleration #3': 200.0,
    'Particle Shader - Scale Key 1': 15.0,
    'Particle Shader - Scale Key 2': 28.0,
    'Particle Shader - Scale Key 1 Time': 0.1,
    'Particle Shader - Scale Key 2 Time': 1.0,
    'Color Key 1 - Color': (121, 117, 210),
    'Color Key 2 - Color': (211, 204, 255),
    'Color Key 3 - Color': (32, 32, 89),
    'Color Key 1 - Color Alpha': 0.5,
    'Color Key 2 - Color Alpha': 1.0,
    'Color Key 3 - Color Alpha': 0.5,
    'Color Key 1 - Color Key Time': 0.1,
    'Color Key 2 - Color Key Time': 0.25,
    'Color Key 3 - Color Key Time': 0.75,
    'Particle Shader - Initial Speed Along Normal +/-': 10.0,
    'Particle Shader - Initial Rotation (deg) +/-': 180.0,
    'Particle Shader - Rotation Speed (deg/sec)': 80.0,
    'Particle Shader - Rotation Speed (deg/sec) +/-': 50.0,
    'Holes - Start Time': 0.0,
    'Holes - End Time': 1.0,
    'Holes - Start Val': 255.0,
    'Holes - End Val': 0.0,
    'Explosion Wind Speed': 0.0,
    'Texture Count U': 2,
    'Texture Count V': 2,
    'Addon Models - Scale In Time': 1.0,
    'Fill/Texture Effect - Color Key 2': (248, 248, 250),
    'Fill/Texture Effect - Color Key 3': (144, 144, 144),
    'Fill Color Key 1 - Scale': 1.0,
    'Fill Color Key 2 - Scale': 2.0,
    'Fill Color Key 3 - Scale': 2.0,
    'Fill Color Key 1 - Time': 0.0,
    'Fill Color Key 2 - Time': 0.2,
    'Fill Color Key 3 - Time': 1.0,
    'Color Scale': 1.25,
    'Birth Position Offset': 0.0,
    'Start Frame Variation': 31,
    'End Frame': 31,
    'Loop Start Frame': 31,
    'Frame Count': 24,
    'Fill/Texture Effect - Texture Scale (U)': 1.5,
    'Fill/Texture Effect - Texture Scale (V)': 1.5,
}

EXPECTED_VANILLA = {
    # raw dword is 0x4E000000: black with alpha 78 (alpha sits in byte 3)
    'Membrane Shader - Specular Color': (0, 0, 0),
    'Membrane Shader - Specular Strength': 5,
    'Membrane Shader - Specular Color Scale': 1,
    'Membrane Shader - Unknown12': 3,
    'Fill/Texture Effect - Color Key 1': (102, 102, 102),
    'Fill/Texture Effect - Alpha Fade In Time': 0.5,
    'Fill/Texture Effect - Full Alpha Time': 0.1,
    'Fill/Texture Effect - Alpha Fade Out Time': 0.5,
    'Fill/Texture Effect - Presistent Alpha Ratio': 0.05,
    'Fill/Texture Effect - Texture Animation Speed (V)': 0.1,
    'Edge Effect - Fall Off': 1.2,
    'Edge Effect - Color': (63, 63, 107),
    'Edge Effect - Persistent Alpha Ratio': 0.9,
    'Edge Effect - Alpha Pulse Amplitude': 0.1,
    'Edge Effect - Alpha Pulse Frequency': 0.4,
    'Fill/Texture Effect - Full Alpha Ratio': 0.12,
    'Edge Effect - Full Alpha Ratio': 1.0,
    'Particle Shader - Particle Birth Ramp Up Time': 0.5,
    'Particle Shader - Full Particle Birth Time': 0.25,
    'Particle Shader - Particle Birth Ramp Down Time': 0.5,
    'Particle Shader - Full Particle Birth Ratio': 40.0,
    'Particle Shader - Persistant Particle Count': 0.0,
    'Particle Shader - Particle Lifetime': 0.2,
    'Particle Shader - Particle Lifetime +/-': 0.05,
    'Particle Shader - Initial Speed Along Normal': 20.0,
    'Particle Shader - Acceleration #3': 100.0,
    'Particle Shader - Scale Key 1': 4.0,
    'Particle Shader - Scale Key 2': 22.0,
    'Color Key 1 - Color': (79, 83, 136),
    'Color Key 2 - Color': (176, 170, 236),
    'Color Key 3 - Color': (79, 83, 136),
    'Color Key 1 - Color Alpha': 0.0,
    'Color Key 2 - Color Alpha': 1.0,
    'Color Key 3 - Color Alpha': 0.8,
    'Color Key 2 - Color Key Time': 0.3,
    'Color Key 3 - Color Key Time': 0.75,
    'Particle Shader - Initial Speed Along Normal +/-': 0.0,
    'Particle Shader - Initial Rotation (deg) +/-': 5.0,
    'Holes - End Time': 10.0,
    'Texture Count U': 2,
    'Texture Count V': 2,
    'Fill/Texture Effect - Color Key 2': (95, 95, 95),
    'Fill/Texture Effect - Color Key 3': (79, 79, 79),
    'Fill Color Key 1 - Scale': 1.2,
    'Fill Color Key 2 - Scale': 1.2,
    'Fill Color Key 3 - Scale': 1.2,
    'Color Scale': 1.0,
    'Flags': 0x00000004,   # Membrane Grayscale Alpha
}


def find_data(path, formid):
    with open(path, 'rb') as f:
        b = f.read()
    off, n = 0, len(b)
    while off + 24 <= n:
        sig = b[off:off + 4]
        size = struct.unpack_from('<I', b, off + 4)[0]
        if sig == b'GRUP':
            off += 24
            continue
        if off + 24 + size > n:
            break
        fid = struct.unpack_from('<I', b, off + 12)[0]
        if fid == formid:
            o, end = off + 24, off + 24 + size
            while o + 6 <= end:
                st = b[o:o + 4]
                sl = struct.unpack_from('<H', b, o + 4)[0]
                o += 6
                if st == b'DATA':
                    return b[o:o + sl]
                o += sl
        off += 24 + size
    return None


def read_field(data, name):
    off, kind = BY_NAME[name]
    if kind == 'f32':
        return round(struct.unpack_from('<f', data, off)[0], 6)
    if kind == 'u32':
        return struct.unpack_from('<I', data, off)[0]
    if kind == 'rgb':
        dw = struct.unpack_from('<I', data, off)[0]
        # colours are stored with red in the LOW byte (0x00BBGGRR)
        return (dw & 0xFF, (dw >> 8) & 0xFF, (dw >> 16) & 0xFF)
    raise ValueError(kind)


def check(label, path, formid, expected):
    data = find_data(path, formid)
    if data is None:
        print(f'!! {label}: DATA not found')
        return 0, 0
    ok = bad = 0
    for name, want in expected.items():
        got = read_field(data, name)
        if isinstance(want, float):
            good = abs(got - want) < 1e-4
        else:
            good = got == want
        if good:
            ok += 1
        else:
            bad += 1
            off, kind = BY_NAME[name]
            print(f'   MISMATCH {label}: {name}\n'
                  f'            offset={off} kind={kind} got={got} want={want}')
    return ok, bad


if __name__ == '__main__':
    mod = SPELLSIPHON_ESP
    sky = os.path.join(RESEARCH, 'stage', 'Skyrim.esm')
    print('validating layout against xDump-decoded values...\n')
    a_ok, a_bad = check('KSSC_ShockShader', mod, 0x0403603E, EXPECTED_MOD)
    b_ok, b_bad = check('AlchArmorShockFXS', sky, 0x0010BEAC, EXPECTED_VANILLA)
    print(f'\nKSSC_ShockShader : {a_ok} ok, {a_bad} mismatched')
    print(f'AlchArmorShockFXS: {b_ok} ok, {b_bad} mismatched')
    print('LAYOUT VALIDATED' if (a_bad == 0 and b_bad == 0) else 'LAYOUT NEEDS FIXES')
    sys.exit(1 if (a_bad or b_bad) else 0)
