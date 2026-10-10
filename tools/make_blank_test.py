"""Diagnostic patch: fully transparent shock textures.

Purpose: decide once and for all whether the white lightning ring is drawn by
the shock TEXTURES or by GEOMETRY / some other shader.

    ring disappears  -> it is texture-driven; tune the alpha levels
    ring remains     -> it is geometry (a .nif) or a different effect entirely

Transparent textures make every shock effect in the game invisible, which is
fine for a one-off diagnostic run.
"""
from __future__ import annotations

import os
import sys
import zipfile

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
OUT = os.path.join(PROJECT, 'dist-tex', 'Spellsiphon - Shock Test (transparent)')

FILES = [
    ('shocktile01.dds', 'textures/effects/shocktile01.dds'),
    ('shockparticles02.dds', 'textures/effects/shockparticles02.dds'),
    ('gradshockhit.dds', 'textures/effects/gradients/gradshockhit.dds'),
    ('gradshockencharmor.dds', 'textures/effects/gradients/gradshockencharmor.dds'),
]


def find_vanilla(name):
    for root, _d, files in os.walk(VANILLA):
        for f in files:
            if f.lower() == name.lower():
                return os.path.join(root, f)
    return None


README = """Spellsiphon - Shock Test (transparent)  - DIAGNOSTIC ONLY
=========================================================

This is a TEST mod, not a fix. It replaces the shock effect textures with fully
transparent (empty) images.

What it tells us
----------------
Enable it, load a save, and watch the white lightning ring around the character:

  * ring DISAPPEARS -> the ring is drawn by these textures. The fix is a matter
    of tuning alpha, and we already have working levers.
  * ring REMAINS    -> the ring is geometry (a .nif model) or a completely
    different effect, and no amount of texture or shader-record editing will
    remove it. We would then target the mesh instead.

Side effect: every shock effect in the game becomes invisible while this is
enabled. That is expected - enable it only for a quick look, then disable it.
"""


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    print(f"{'file':<26}{'source':<14}{'size':<12}{'bytes':>10}")
    print('-' * 64)
    for vname, rel in FILES:
        src = find_vanilla(vname)
        if not src:
            print(f'{vname:<26}VANILLA NOT FOUND')
            continue
        img = open_dds(src)
        # keep dimensions, drop all colour and alpha
        blank = Image.new('RGBA', img.size, (255, 255, 255, 0))
        dst = os.path.join(OUT, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        size = save_dds_bgra(blank, dst)
        print(f'{vname:<26}{"vanilla":<14}{img.width}x{img.height:<7}{size:>10,}')
        print(f'    -> {dst}')

    with open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write(README)
    with open(os.path.join(OUT, 'meta.ini'), 'w', encoding='utf-8') as f:
        f.write('[General]\n'
                'gameName=Skyrim Special Edition\n'
                'modid=0\nfileid=0\nversion=1.0.0-test\n'
                'notes=DIAGNOSTIC: fully transparent shock textures. Enable, check '
                'whether the lightning ring disappears, then disable again.\n'
                'repository=Manual\n')

    z = OUT + '.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _d, files in os.walk(OUT):
            for fn in files:
                full = os.path.join(root, fn)
                zf.write(full, os.path.relpath(full, OUT))
    print(f'\nzip: {z} ({os.path.getsize(z):,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
