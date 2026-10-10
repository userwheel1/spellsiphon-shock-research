#!/usr/bin/env python3
"""
package_nexus.py - build the final Nexus upload archive.

Produces dist-nexus/Spellsiphon - No Static Aura.zip containing exactly what the
mod ships:

    textures/effects/shocktile01.dds
    textures/effects/shockparticles02.dds
    textures/effects/gradients/gradshockhit.dds
    README.txt
    meta.ini

No plugin, no scripts, no game records - purely a texture replacement.
"""
from __future__ import annotations

import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DIST = os.path.join(PROJECT, 'dist-nexus')

# the validated 'hard' build
SRC = os.path.join(PROJECT, 'dist-tex', 'Spellsiphon - No Static Aura (hard)')
README = os.path.join(PROJECT, 'docs', 'README-no-static-aura.txt')

ARCHIVE_NAME = 'Spellsiphon - No Static Aura'
VERSION = '1.0.0'


def main() -> int:
    if not os.path.isdir(SRC):
        print(f'missing source build: {SRC}')
        return 1
    if not os.path.isfile(README):
        print(f'missing README: {README}')
        return 1

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f'{ARCHIVE_NAME}.zip')
    if os.path.isfile(out):
        os.remove(out)

    entries = []
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        # module files (README replaced below by the publication version)
        for root, _dirs, files in os.walk(SRC):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, SRC)
                if rel.lower() in ('readme.txt', 'readme.md', 'meta.ini'):
                    continue
                zf.write(full, rel)
                entries.append(rel)
        zf.write(README, 'README.txt')
        entries.append('README.txt')
        # keep meta.ini in sync with the published build
        meta = (
            '[General]\n'
            'gameName=Skyrim Special Edition\n'
            'modid=0\n'
            'fileid=0\n'
            f'version={VERSION}\n'
            'repository=Manual\n'
            'notes=Texture-only replacement of ShockTile01.dds, '
            'ShockParticles02.dds and GradShockHit.dds. Removes the Woven Power '
            'static aura. No plugin. Must load below Voltage / RUSTIC DAEDRA SSE / '
            'Particle Patch for ENB.\n'
        )
        zf.writestr('meta.ini', meta)

    print(f'archive : {out}')
    print(f'size    : {os.path.getsize(out):,} bytes')
    print(f'version : {VERSION}')
    print('contents:')
    with zipfile.ZipFile(out) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            print(f'   {info.filename}   ({info.file_size:,} bytes)')
        plugins = [i.filename for i in zf.infolist()
                   if i.filename.lower().endswith(('.esp', '.esm', '.esl'))]
    print(f'\nplugins inside: {plugins if plugins else "none (expected)"}')
    return 0 if not plugins else 1


if __name__ == '__main__':
    sys.exit(main())
