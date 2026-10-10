"""Build the texture-level fix using the validated ddsio module.

Why this exists
---------------
tools/compare_textures.py measured the shock textures actually installed in the
modlist against the vanilla ones from Skyrim - Textures5.bsa:

    texture                vanilla   installed   source of the replacer
    ShockTile01.dds          42.0      26.8      Voltage
    ShockParticles02.dds      6.7      12.5      Rustic Daedra SSE   (1.9x)
    GradShockHit.dds         21.8      28.0      Voltage             (1.3x)

(energy = luminance x alpha = how much light the layer really contributes)

The Effect Shader edits alone cannot fix this: swapping to vanilla shader
textures made things *worse*, because the replacement gradients the game is told
to use (GradShockEnchArmor) are themselves brighter and more opaque.

So the fix has to be at the texture level: ship replacement DDS files that sort
above every texture replacer.

Levels
------
    strong  - very calm; good first test to prove the mechanism
    medium  - clearly reduced but still present
    light   - a gentle reduction
"""
from __future__ import annotations

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ddsio import open_dds, save_dds_bgra  # noqa: E402

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

PROJECT = os.path.dirname(HERE)
VANILLA = VANILLA_TEX_DIR
OUTROOT = os.path.join(PROJECT, 'dist-tex')

# candidate target energies per level, and the measured value currently
# installed in the Merethic build (used for the report)
PLAN = [
    # vanilla file, output rel path, installed energy, per-level targets, note
    ('shocktile01.dds', 'shocktile01.dds', 26.8,
     {'strong': 5.0, 'medium': 8.0, 'light': 14.0},
     'corner/tile fill - the biggest contributor to screen coverage'),
    ('shockparticles02.dds', 'shockparticles02.dds', 12.5,
     {'strong': 3.0, 'medium': 4.5, 'light': 7.0},
     'spark particles - installed version is 1.9x vanilla (Rustic Daedra)'),
    ('gradshockhit.dds', 'gradients/gradshockhit.dds', 28.0,
     {'strong': 5.0, 'medium': 8.0, 'light': 14.0},
     'impact gradient - installed version is 1.3x vanilla (Voltage)'),
]


def energy(img: Image.Image) -> float:
    px = list(img.convert('RGBA').resize((192, 192)).getdata())
    n = len(px)
    return sum((0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2]) * q[3] / 255
               for q in px) / n


def find_vanilla(name: str):
    for root, _d, files in os.walk(VANILLA):
        for f in files:
            if f.lower() == name.lower():
                return os.path.join(root, f)
    return None


def scale_alpha(img: Image.Image, factor: float) -> Image.Image:
    r, g, b, a = img.convert('RGBA').split()
    a2 = a.point(lambda v: max(0, min(255, int(v * factor))))
    return Image.merge('RGBA', (r, g, b, a2))


def build(level: str) -> int:
    out_dir = os.path.join(OUTROOT, 'textures', 'effects')
    print(f'level = {level}\n')
    print(f"{'texture':<24}{'vanilla':>9}{'installed':>11}{'target':>8}"
          f"{'result':>8}{'alpha':>7}{'vs inst':>9}")
    print('-' * 78)
    for vname, rel, installed, targets, note in PLAN:
        vpath = find_vanilla(vname)
        if not vpath:
            print(f'{vname:<24} VANILLA NOT FOUND'); continue
        src = open_dds(vpath)
        ve = energy(src)
        target = targets[level]
        factor = max(0.02, min(1.0, target / ve)) if ve else 0.1
        out = scale_alpha(src, factor)
        oe = energy(out)
        dst = os.path.join(out_dir, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        size = save_dds_bgra(out, dst)
        ratio = oe / installed if installed else 0
        print(f'{vname:<24}{ve:>9.1f}{installed:>11.1f}{target:>8.1f}'
              f'{oe:>8.1f}{factor:>7.2f}{ratio:>8.2f}x')
        print(f'    {note}')
        print(f'    -> {dst}  ({size:,} bytes)')
    return 0


if __name__ == '__main__':
    lvl = 'strong'
    if '--level' in sys.argv:
        lvl = sys.argv[sys.argv.index('--level') + 1]
    sys.exit(build(lvl))
