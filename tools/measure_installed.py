"""Measure the texture reduction actually installed in the modlist."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ddsio import open_dds  # noqa: E402

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

MODS = MODS_DIR
PATCH = os.path.join(MODS, 'Spellsiphon - Soft Shock Textures (strong)')

ROWS = [
    ('shocktile01.dds',
     r'Voltage\textures\effects\shocktile01.dds',
     r'textures\effects\shocktile01.dds'),
    ('shockparticles02.dds',
     r'RUSTIC DAEDRA SSE\textures\effects\shockparticles02.dds',
     r'textures\effects\shockparticles02.dds'),
    ('gradshockhit.dds',
     r'Voltage\textures\effects\gradients\gradshockhit.dds',
     r'textures\effects\gradients\gradshockhit.dds'),
]


def energy(p):
    img = open_dds(p)
    px = list(img.resize((160, 160)).getdata())
    n = len(px)
    return sum((0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2]) * q[3] / 255
               for q in px) / n


print(f"{'texture':<24}{'before':>8}{'after':>8}{'reduction':>11}   source")
print('-' * 86)
for name, oldrel, newrel in ROWS:
    old = energy(os.path.join(MODS, oldrel))
    new = energy(os.path.join(PATCH, newrel))
    src = oldrel.split('\\')[0]
    print(f'{name:<24}{old:>8.1f}{new:>8.1f}{100 * (1 - new / old):>10.0f}%   '
          f'{src} -> Spellsiphon - Soft Shock Textures')
