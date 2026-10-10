"""Generate the three texture-fix variants, each as a MO2-ready folder + zip."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PROJECT = os.path.dirname(HERE)
DIST = os.path.join(PROJECT, 'dist-tex')

sys.path.insert(0, HERE)
import make_texture_fix as mtf  # noqa: E402

BASE = 'Spellsiphon - Soft Shock Textures'

README = """Spellsiphon - Soft Shock Textures  ({LEVEL})
====================================================

A pure TEXTURE mod. It ships replacement .dds files for the three textures that
SpellSiphon's Life (shock) effect uses, calibrated to be much dimmer than the
versions currently installed by texture replacers.

WHY A TEXTURE PATCH
-------------------
Replacing the Effect Shader records alone does not work here, because the
brightness comes from the textures, not the shader. Measured in this modlist:

    texture                vanilla   installed   replacer
    ShockTile01.dds          41.9      26.8      Voltage
    ShockParticles02.dds      6.7      12.5      Rustic Daedra SSE  (1.9x)
    GradShockHit.dds         21.8      28.0      Voltage            (1.3x)

(energy = luminance x alpha = how much light the layer actually adds)

Level {LEVEL} targets:
    ShockTile01.dds        -> {E_TILE}
    ShockParticles02.dds   -> {E_PART}
    GradShockHit.dds       -> {E_GRAD}

INSTALL
-------
1. Install as a normal mod.
2. IMPORTANT: place it BELOW (higher priority than) every texture replacer in
   the LEFT pane - at minimum below "Voltage", "RUSTIC DAEDRA SSE" and
   "Particle Patch for ENB". Otherwise its files lose the conflict and nothing
   changes.
3. The texture files apply on the next game launch; no plugin is involved.

UNINSTALL
---------
Disable the mod. No original file is modified.

NOTES
-----
A texture-only patch: replaces three .dds textures of the Life effect with
dimmed versions. No plugin.

In Mod Organizer 2 it must sit BELOW every texture mod (at minimum below
Voltage, RUSTIC DAEDRA SSE and Particle Patch for ENB), otherwise its files
lose the conflict and nothing changes.
"""

LEVELS = ['strong', 'medium', 'light']

TITLES = {
    'strong': 'strong - quietest, useful for proving the mechanism',
    'medium': 'medium - clearly weaker, still visible',
    'light': 'light - gentle reduction',
}


def main() -> int:
    # make_texture_fix writes into dist-tex/textures; generate each level into
    # its own folder instead.
    results = {}
    for lvl in LEVELS:
        target_dir = os.path.join(DIST, f'{BASE} ({lvl})')
        mtf.OUTROOT = target_dir
        mtf.OUT = None  # not used any more
        os.makedirs(os.path.join(target_dir, 'textures', 'effects'), exist_ok=True)
        print(f'\n=== building {lvl} -> {target_dir}')
        # temporarily redirect the output root used by build()
        old = mtf.OUTROOT
        try:
            mtf.OUTROOT = target_dir
            rc = mtf.build(lvl)
        finally:
            mtf.OUTROOT = old

        # read back the achieved energies for the README
        from ddsio import open_dds
        achieved = {}
        for vname, rel, installed, targets, note in mtf.PLAN:
            p = os.path.join(target_dir, 'textures', 'effects',
                             rel.replace('/', os.sep))
            achieved[vname] = mtf.energy(open_dds(p)) if os.path.isfile(p) else 0.0

        with open(os.path.join(target_dir, 'README.txt'), 'w', encoding='utf-8') as f:
            f.write(README.format(
                LEVEL=lvl,
                E_TILE=f'{achieved.get("shocktile01.dds", 0):.1f}',
                E_PART=f'{achieved.get("shockparticles02.dds", 0):.1f}',
                E_GRAD=f'{achieved.get("gradshockhit.dds", 0):.1f}'))

        with open(os.path.join(target_dir, 'meta.ini'), 'w', encoding='utf-8') as f:
            f.write('[General]\n'
                    'gameName=Skyrim Special Edition\n'
                    'modid=0\nfileid=0\nversion=1.0.0\n'
                    f'notes=Soft Shock Textures ({lvl}) - replaces ShockTile01.dds, '
                    'ShockParticles02.dds and GradShockHit.dds with dimmed versions. '
                    'Must load BELOW Voltage / RUSTIC DAEDRA SSE / Particle Patch for ENB.\n'
                    'repository=Manual\n')
        results[lvl] = target_dir
        print(f'  -> packaged {target_dir}')

    # fresh zips
    for lvl, d in results.items():
        z = d + '.zip'
        if os.path.isfile(z):
            os.remove(z)
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(d):
                for fn in files:
                    full = os.path.join(root, fn)
                    zf.write(full, os.path.relpath(full, d))
        print(f'zip: {z}  ({os.path.getsize(z):,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
