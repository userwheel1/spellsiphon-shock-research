"""Targeted removal of the Woven Power static aura.

Findings that drive this build
------------------------------
* Replacing the textures with FULLY TRANSPARENT ones removed the static
  electricity around the character - so the aura is drawn by these textures,
  not by a shader record, a script property or a mesh.
* The 'strong' level (-82% energy) did NOT remove it, because the aura survives
  as long as any opacity remains.
* Making ICON/ICO2 fully transparent exposed flat 2-D quads on the hand: that is
  the shader's geometry, normally covered by the texture.

So: kill the two textures that produce the lightning (tile + particles) with a
zero alpha, and keep a faint gradient so the remaining shock visuals still read
as electricity rather than as bare geometry.

Levels
------
  hard    ICON a=0, ICO2 a=0, NAM8 kept at 0.35  - aura fully gone
  medium  ICON a=0.06, ICO2 a=0, NAM8 at 0.45    - aura almost gone
"""
from __future__ import annotations

import os
import struct
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
OUTROOT = os.path.join(PROJECT, 'dist-tex')

PLAN = {
    'hard': {
        'shocktile01.dds': 0.0,
        'shockparticles02.dds': 0.0,
        'gradshockhit.dds': 0.35,
    },
    'medium': {
        'shocktile01.dds': 0.06,
        'shockparticles02.dds': 0.0,
        'gradshockhit.dds': 0.45,
    },
}

REL = {
    'shocktile01.dds': 'textures/effects/shocktile01.dds',
    'shockparticles02.dds': 'textures/effects/shockparticles02.dds',
    'gradshockhit.dds': 'textures/effects/gradients/gradshockhit.dds',
}

INSTALLED = {
    'shocktile01.dds': 26.8,
    'shockparticles02.dds': 12.5,
    'gradshockhit.dds': 28.0,
}


def find_vanilla(name):
    for root, _d, files in os.walk(VANILLA):
        for f in files:
            if f.lower() == name.lower():
                return os.path.join(root, f)
    return None


def energy(img):
    px = list(img.convert('RGBA').resize((192, 192)).getdata())
    n = len(px)
    return sum((0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2]) * q[3] / 255
               for q in px) / n


def scale_alpha(img, f):
    r, g, b, a = img.convert('RGBA').split()
    a2 = a.point(lambda v: max(0, min(255, int(v * f))))
    return Image.merge('RGBA', (r, g, b, a2))


README = """Spellsiphon - No Static Aura  ({LEVEL})
==========================================

Replaces the shock effect textures so the static electricity that flickers
around the character while Woven Power accumulates is gone.

HOW THIS WAS ESTABLISHED
------------------------
Fully transparent versions of these textures removed the aura completely, while
an 82% reduction did not. That proves the aura is drawn by these textures and
that it survives as long as any opacity is left - so the tile and particle
textures are zeroed out.

Level {LEVEL}:
    ShockTile01.dds        alpha x{A1}
    ShockParticles02.dds   alpha x{A2}
    GradShockHit.dds       alpha x{A3}   (kept faintly so the remaining shock
                                          visuals still read as electricity
                                          instead of bare 2-D geometry)

This is a TEXTURE mod - it contains no plugin. Nothing but the visuals changes:
Woven Power accumulation, damage and all mechanics are untouched.

INSTALL
-------
Place this mod BELOW (higher priority than) Voltage, RUSTIC DAEDRA SSE and
Particle Patch for ENB in the left pane, otherwise its files lose the conflict.

NOTES
-----
A texture mod: no plugin, so nothing about the mechanics changes. It only
affects what the electric effect looks like.

In Mod Organizer 2 this mod must sit BELOW - higher priority than - any mod
that ships the same files, otherwise it loses the conflict and nothing changes.
"""


def main() -> int:
    results = {}
    for level, plan in PLAN.items():
        out_dir = os.path.join(OUTROOT, f'Spellsiphon - No Static Aura ({level})')
        os.makedirs(os.path.join(out_dir, 'textures', 'effects'), exist_ok=True)
        print(f'\n=== {level} -> {out_dir}')
        print(f"{'texture':<24}{'installed':>10}{'alpha':>8}{'result':>9}{'vs inst':>10}")
        print('-' * 62)
        achieved = {}
        for name, af in plan.items():
            src = find_vanilla(name)
            if not src:
                print(f'{name:<24} VANILLA NOT FOUND'); continue
            img = scale_alpha(open_dds(src), af)
            dst = os.path.join(out_dir, REL[name].replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            save_dds_bgra(img, dst)
            e = energy(img)
            achieved[name] = e
            inst = INSTALLED[name]
            print(f'{name:<24}{inst:>10.1f}{af:>8.2f}{e:>9.1f}'
                  f'{(e / inst if inst else 0):>9.2f}x')
        with open(os.path.join(out_dir, 'README.txt'), 'w', encoding='utf-8') as f:
            f.write(README.format(
                LEVEL=level,
                A1=f"{plan['shocktile01.dds']:.2f}",
                A2=f"{plan['shockparticles02.dds']:.2f}",
                A3=f"{plan['gradshockhit.dds']:.2f}"))
        with open(os.path.join(out_dir, 'meta.ini'), 'w', encoding='utf-8') as f:
            f.write('[General]\ngameName=Skyrim Special Edition\nmodid=0\nfileid=0\n'
                    f'version=1.0.0\nnotes=Removes the Woven Power static aura by '
                    f'zeroing ShockTile01/ShockParticles02 alpha ({level}). '
                    f'Must load below Voltage / RUSTIC DAEDRA SSE / '
                    f'Particle Patch for ENB.\nrepository=Manual\n')
        z = out_dir + '.zip'
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _d, files in os.walk(out_dir):
                for fn in files:
                    full = os.path.join(root, fn)
                    zf.write(full, os.path.relpath(full, out_dir))
        results[level] = z
        print(f'  zip: {z} ({os.path.getsize(z):,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
