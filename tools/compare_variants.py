#!/usr/bin/env python3
"""
compare_variants.py - explain what each variant changes visually.

Reads the original Spellsiphon shader and each variant's payload, then prints a
field-by-field comparison of the parameters that control how much of the screen
the effect covers.

Usage:
    python tools/compare_variants.py
"""
from __future__ import annotations

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from efsh_layout import BY_NAME  # noqa: E402

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

SPELLSIPHON_ESP = SPELLSIPHON_ESP
SKYRIM_ESM = SKYRIM_ESM

TARGET_FORMID = 0x0403603E
SOURCES = {
    'Vanilla Shock': (SKYRIM_ESM, 0x0010BEAC, 'AlchArmorShockFXS'),
    'Mage Glow': (SKYRIM_ESM, 0x00094160, 'MagicArmorOakFleshFXS'),
}

# Parameters that decide how much of the screen the effect occupies, grouped for
# readability.  Names must exist in efsh_layout.BY_NAME.
GROUPS = [
    ('Fill (membrane)', [
        'Fill/Texture Effect - Presistent Alpha Ratio',
        'Fill/Texture Effect - Full Alpha Ratio',
        'Fill Color Key 1 - Scale',
        'Fill Color Key 2 - Scale',
        'Fill Color Key 3 - Scale',
        'Fill/Texture Effect - Texture Scale (U)',
        'Fill/Texture Effect - Texture Scale (V)',
    ]),
    ('Edge (rim)', [
        'Edge Effect - Persistent Alpha Ratio',
        'Edge Effect - Full Alpha Ratio',
        'Edge Effect - Fall Off',
    ]),
    ('Particles', [
        'Particle Shader - Persistant Particle Count',
        'Particle Shader - Full Particle Birth Ratio',
        'Particle Shader - Scale Key 1',
        'Particle Shader - Scale Key 2',
        'Particle Shader - Particle Lifetime',
        'Particle Shader - Initial Speed Along Normal',
        'Particle Shader - Initial Speed Along Normal +/-',
        'Particle Shader - Initial Rotation (deg) +/-',
        'Particle Shader - Rotation Speed (deg/sec)',
        'Particle Shader - Acceleration #3',
    ]),
    ('Colour and alpha', [
        'Color Key 1 - Color',
        'Color Key 2 - Color',
        'Color Key 3 - Color',
        'Color Key 1 - Color Alpha',
        'Color Key 2 - Color Alpha',
        'Color Key 3 - Color Alpha',
        'Color Scale',
    ]),
    ('Other', [
        'Holes - End Time',
        'Flags',
        'Ambient Sound',
    ]),
]


def read(path):
    with open(path, 'rb') as fh:
        return fh.read()


def find_data(buf, formid):
    off, n = 0, len(buf)
    while off + 24 <= n:
        sig = buf[off:off + 4]
        size = struct.unpack_from('<I', buf, off + 4)[0]
        if sig == b'GRUP':
            off += 24
            continue
        if off + 24 + size > n:
            break
        if struct.unpack_from('<I', buf, off + 12)[0] == formid:
            o, end = off + 24, off + 24 + size
            while o + 6 <= end:
                st = buf[o:o + 4]
                sl = struct.unpack_from('<H', buf, o + 4)[0]
                o += 6
                if st == b'DATA':
                    return buf[o:o + sl]
                o += sl
        off += 24 + size
    return None


def value(data, name):
    off, kind = BY_NAME[name]
    if kind == 'f32':
        return struct.unpack_from('<f', data, off)[0]
    if kind == 'u32':
        return struct.unpack_from('<I', data, off)[0]
    dw = struct.unpack_from('<I', data, off)[0]
    return (dw & 0xFF, (dw >> 8) & 0xFF, (dw >> 16) & 0xFF)


def fmt(v):
    if isinstance(v, tuple):
        return f"RGB{v}"
    if isinstance(v, float):
        return f'{v:g}'
    return f'0x{v:08X}' if v > 0xFFFF else str(v)


def main() -> int:
    orig = find_data(read(SPELLSIPHON_ESP), TARGET_FORMID)
    if orig is None:
        print('original shader not found')
        return 1

    payloads = {'Original (SpellSiphon 5.28)': orig}
    for label, (path, fid, edid) in SOURCES.items():
        d = find_data(read(path), fid)
        payloads[label] = d

    labels = list(payloads)
    for group, fields in GROUPS:
        print(f'\n--- {group} ' + '-' * max(0, 58 - len(group)))
        head = f"{'parameter':<46}" + ''.join(f'{l[:14]:>16}' for l in labels)
        print(head)
        for fname in fields:
            if fname not in BY_NAME:
                continue
            row = f'{fname:<46}'
            for l in labels:
                d = payloads[l]
                if d is None:
                    row += f'{"-":>16}'
                else:
                    row += f'{fmt(value(d, fname)):>16}'
            print(row)

    print('\nTextures:')
    tex = {
        'Original': (SPELLSIPHON_ESP, TARGET_FORMID),
        'Vanilla Shock': (SKYRIM_ESM, 0x0010BEAC),
        'Mage Glow': (SKYRIM_ESM, 0x00094160),
    }
    for label, (path, fid) in tex.items():
        buf = read(path)
        off, n = 0, len(buf)
        got = {}
        while off + 24 <= n:
            sig = buf[off:off + 4]
            size = struct.unpack_from('<I', buf, off + 4)[0]
            if sig == b'GRUP':
                off += 24
                continue
            if off + 24 + size > n:
                break
            if struct.unpack_from('<I', buf, off + 12)[0] == fid:
                o, end = off + 24, off + 24 + size
                while o + 6 <= end:
                    st = buf[o:o + 4]
                    sl = struct.unpack_from('<H', buf, o + 4)[0]
                    o += 6
                    if st in (b'ICON', b'ICO2', b'NAM8'):
                        got[st.decode()] = buf[o:o + sl].split(b'\x00')[0].decode(
                            'utf-8', 'replace')
                    o += sl
            off += 24 + size
        print(f'  {label:<28} ICON={os.path.basename(got.get("ICON", "")) or "-":<24} '
              f'NAM8={os.path.basename(got.get("NAM8", "")) or "-"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
