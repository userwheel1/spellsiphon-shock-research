"""Extract the vanilla shock textures from the game BSA and compare them with the
texture-replacer versions installed in the modlist.

This decides whether a texture-level fix is what is actually needed.
"""
import os
import subprocess
import struct
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DATA = SKYRIM_DATA
BSARCH = BSARCH
MODS = MODS_DIR
WORK = os.path.join(RESEARCH_DIR, 'bsa_extract')

WANT = [
    r'textures\effects\shocktile01.dds',
    r'textures\effects\shockparticles02.dds',
    r'textures\effects\gradients\gradshockhit.dds',
    r'textures\effects\gradients\gradshockencharmor.dds',
    r'textures\effects\darkswirls.dds',
]

MOD_COPIES = {
    r'textures\effects\shocktile01.dds':
        [r'Voltage\textures\effects\shocktile01.dds'],
    r'textures\effects\shockparticles02.dds':
        [r'RUSTIC DAEDRA SSE\textures\effects\shockparticles02.dds',
         r'Voltage\textures\effects\shockparticles02.dds'],
    r'textures\effects\gradients\gradshockhit.dds':
        [r'Voltage\textures\effects\gradients\gradshockhit.dds'],
    r'textures\effects\gradients\gradshockencharmor.dds':
        [r'Voltage\textures\effects\gradients\gradshockencharmor.dds'],
    r'textures\effects\darkswirls.dds':
        [r'Particle Patch for ENB\textures\effects\darkswirls.dds',
         r'Inferno - Fire Effects Redux\textures\effects\darkswirls.dds'],
}


def extract_from_bsa(bsa, names, dest):
    """BSArch can only unpack whole archives; unpack once and keep what we need."""
    os.makedirs(dest, exist_ok=True)
    subprocess.run([BSARCH, 'unpack', bsa, dest, '-q'],
                   check=True, capture_output=True)
    found = []
    for n in names:
        p = os.path.join(dest, n)
        if os.path.isfile(p):
            found.append(p)
    return found


def main():
    from make_comparison import dds_image  # validated decoder

    def stats(img):
        px = img.convert('RGBA').resize((256, 256)).getdata()
        k = len(px)
        lum = sum(0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2] for q in px) / k
        al = sum(q[3] for q in px) / k
        en = sum((0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2]) * q[3] / 255
                 for q in px) / k
        return lum, al, en

    # figure out which BSA holds each texture via -list
    locations = {}
    for idx in range(4, 9):
        bsa = os.path.join(DATA, f'Skyrim - Textures{idx}.bsa')
        if not os.path.isfile(bsa):
            continue
        out = subprocess.run([BSARCH, bsa, '-list'], capture_output=True,
                             text=True).stdout.lower()
        for w in WANT:
            if w in out:
                locations[w] = bsa

    print('=== vanilla textures: location ===')
    for w in WANT:
        print(f'  {os.path.basename(w):<28} {os.path.basename(locations.get(w, "NOT FOUND"))}')

    # unpack the archives we need (once each)
    unpacked = {}
    for w, bsa in locations.items():
        if bsa not in unpacked:
            dest = os.path.join(WORK, os.path.splitext(os.path.basename(bsa))[0])
            print(f'\nunpacking {os.path.basename(bsa)} -> {dest} ...')
            extract_from_bsa(bsa, WANT, dest)
            unpacked[bsa] = dest

    print(f"\n{'texture':<28}{'source':<34}{'size':<12}{'lum':>8}{'alpha':>8}{'energy':>9}")
    print('-' * 100)
    for w in WANT:
        name = os.path.basename(w)
        # vanilla
        bsa = locations.get(w)
        if bsa:
            p = os.path.join(unpacked[bsa], w)
            if os.path.isfile(p):
                img = dds_image(p)
                l, a, e = stats(img)
                print(f'{name:<28}{"VANILLA (Skyrim.esm)":<34}'
                      f'{img.width}x{img.height:<6}{l:>8.1f}{a:>8.1f}{e:>9.1f}')
        for rel in MOD_COPIES.get(w, []):
            p = os.path.join(MODS, rel)
            if not os.path.isfile(p):
                continue
            img = dds_image(p)
            l, a, e = stats(img)
            tag = rel.split('\\')[0]
            print(f'{name:<28}{tag[:33]:<34}'
                  f'{img.width}x{img.height:<6}{l:>8.1f}{a:>8.1f}{e:>9.1f}')


if __name__ == '__main__':
    main()
