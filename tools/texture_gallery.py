"""Render the texture-level BEFORE / AFTER comparison.

Columns: what is installed right now -> what the 'strong' texture patch writes.
A vanilla column is included for reference.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ddsio import open_dds  # noqa: E402

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'docs', 'images')
VANILLA = VANILLA_TEX_DIR
MODS = MODS_DIR
TEXPATCH = os.path.join(PROJECT, 'dist-tex',
                        'Spellsiphon - Soft Shock Textures (strong)')

ROWS = [
    ('ShockTile01.dds', 'ICON - tile fill',
     r'textures\effects\shocktile01.dds',
     [r'Voltage\textures\effects\shocktile01.dds']),
    ('ShockParticles02.dds', 'ICO2 - particles',
     r'textures\effects\shockparticles02.dds',
     [r'RUSTIC DAEDRA SSE\textures\effects\shockparticles02.dds',
      r'Voltage\textures\effects\shockparticles02.dds']),
    ('GradShockHit.dds', 'NAM8 - gradient',
     r'textures\effects\gradients\gradshockhit.dds',
     [r'Voltage\textures\effects\gradients\gradshockhit.dds']),
]


def energy(img):
    px = list(img.convert('RGBA').resize((192, 192)).getdata())
    n = len(px)
    return sum((0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2]) * q[3] / 255
               for q in px) / n


def find_vanilla(name):
    for root, _d, files in os.walk(VANILLA):
        for f in files:
            if f.lower() == name.lower():
                return os.path.join(root, f)
    return None


def checker(size, sq=12):
    w, h = size
    img = Image.new('RGBA', size, (58, 58, 66, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, h, sq):
        for x in range(0, w, sq):
            if ((x // sq) + (y // sq)) % 2:
                d.rectangle([x, y, x + sq - 1, y + sq - 1], fill=(92, 92, 102, 255))
    return img


def cell(img, size):
    disp = checker(size)
    t = img.copy()
    t.thumbnail(size, Image.LANCZOS)
    disp.alpha_composite(t, ((size[0] - t.width) // 2, (size[1] - t.height) // 2))
    return disp.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    CW, CH = 250, 250
    pad, head, label_h = 12, 64, 92
    W = pad + 3 * (CW + pad)
    H = head + len(ROWS) * (CH + label_h + pad) + pad
    sheet = Image.new('RGB', (W, H), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    try:
        f_t = ImageFont.truetype('segoeui.ttf', 21)
        f_s = ImageFont.truetype('segoeui.ttf', 14)
        f_b = ImageFont.truetype('segoeuib.ttf', 15)
        f_m = ImageFont.truetype('consola.ttf', 12)
    except Exception:
        f_t = f_s = f_b = f_m = ImageFont.load_default()

    d.text((pad, 10), 'Texture fix: before / after', fill=(255, 255, 255), font=f_t)
    d.text((pad, 34),
           'energy = luminance x alpha - how much light the layer actually adds',
           fill=(158, 168, 188), font=f_s)

    for r, (name, role, rel, mods) in enumerate(ROWS):
        y = head + r * (CH + label_h + pad)
        vpath = find_vanilla(name)
        inst = next((os.path.join(MODS, m) for m in mods
                     if os.path.isfile(os.path.join(MODS, m))), None)
        patch = os.path.join(TEXPATCH, rel)

        variants = [
            ('vanilla', 'VANILLA (Skyrim.esm)', vpath, (150, 170, 230)),
            ('installed', 'INSTALLED now', inst, (232, 110, 110)),
            ('patched', 'AFTER patch (strong)', patch, (110, 215, 130)),
        ]
        e = {}
        for c, (k, title, path, col) in enumerate(variants):
            x = pad + c * (CW + pad)
            if not path or not os.path.isfile(path):
                d.rectangle([x, y, x + CW, y + CH], outline=(70, 70, 80))
                d.text((x + 8, y + 8), 'no file', fill=(200, 90, 90), font=f_s)
                continue
            img = open_dds(path)
            e[k] = energy(img)
            sheet.paste(cell(img, (CW, CH)), (x, y))
            d.rectangle([x, y, x + CW, y + CH], outline=(70, 70, 80))

        ty = y + CH + 4
        d.text((pad, ty), f'{name}   ({role})', fill=(235, 238, 245), font=f_b)
        base = e.get('vanilla') or 1.0
        for c, (k, title, path, col) in enumerate(variants):
            x = pad + c * (CW + pad)
            v = e.get(k)
            d.text((x, ty + 22), title, fill=col, font=f_s)
            if v is not None:
                d.text((x, ty + 42), f'energy {v:5.1f}  ({v / base:4.2f}x vanilla)',
                       fill=(205, 210, 222), font=f_m)
        if e.get('installed') and e.get('patched'):
            d.text((pad, ty + 64),
                   f'removes {100 * (1 - e["patched"] / e["installed"]):.0f}% '
                   f'of the brightness currently in the build',
                   fill=(150, 220, 165), font=f_s)

    p = os.path.join(OUT, 'textures-before-after.png')
    sheet.save(p)
    print('written', p)


if __name__ == '__main__':
    main()
