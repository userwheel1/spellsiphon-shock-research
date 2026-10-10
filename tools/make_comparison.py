"""Build the "before / after" comparison images for the Life draw effect.

Renders a simplified simulation of what the spell shader puts on screen, using
the real texture assets currently installed in the modlist:

  BEFORE (current):  ICON ShockTile01.dds  + ICO2 ShockParticles02.dds
                     + NAM8 GradShockHit.dds         (bright impact gradient)
  AFTER  (patch):    ICON DarkSwirls.dds   + ICO2 ShockParticles02.dds
                     + NAM8 GradShockEnchArmor.dds   (soft armour gradient)

Blending follows the Effect Shader record: additive, with the Fill
"Persistent Alpha Ratio" from each variant applied per layer.
"""
import struct
import os
import math
import random

from PIL import Image, ImageDraw, ImageFont, ImageChops
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

MODS = MODS_DIR
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, 'docs', 'images')

random.seed(7)

TEX = {
    'tile_new':   [r'Voltage\textures\effects\shocktile01.dds'],
    'part_new':   [r'Voltage\textures\effects\shockparticles02.dds',
                   r'RUSTIC DAEDRA SSE\textures\effects\shockparticles02.dds'],
    'grad_new':   [r'Voltage\textures\effects\gradients\gradshockhit.dds'],
    'grad_old':   [r'Voltage\textures\effects\gradients\gradshockencharmor.dds',
                   r'Particle Patch for ENB\textures\effects\gradients\gradshockencharmor.dds'],
    'swirls':     [r'Particle Patch for ENB\textures\effects\darkswirls.dds',
                   r'Inferno - Fire Effects Redux\textures\effects\darkswirls.dds'],
}


def find(key):
    for rel in TEX[key]:
        p = os.path.join(MODS, rel)
        if os.path.isfile(p):
            return p
    return None


# ----------------------------------------------------------------- DDS decode
def dds_image(path):
    d = open(path, 'rb').read()
    h, w = struct.unpack_from('<II', d, 12)
    fourcc = d[84:88]
    off, dxgi = 128, None
    if fourcc == b'DX10':
        dxgi = struct.unpack_from('<I', d, 128)[0]
        off = 148
    block = 8 if (fourcc == b'DXT1' or dxgi in (70, 71, 72)) else 16
    alpha = block == 16
    bw, bh = (w + 3) // 4, (h + 3) // 4
    if len(d) - off < bw * bh * block:
        raise ValueError('truncated dds')
    out = bytearray(w * h * 4)
    pos = off
    for by in range(bh):
        for bx in range(bw):
            blk = d[pos:pos + block]
            if alpha:
                a0, a1 = blk[0], blk[1]
                raw_a = int.from_bytes(blk[2:8], 'little')
                pal_a = [0] * 8
                pal_a[0], pal_a[1] = a0, a1
                if a0 > a1:
                    for i in range(1, 7):
                        pal_a[1 + i] = ((7 - i) * a0 + i * a1) // 7
                else:
                    for i in range(1, 5):
                        pal_a[1 + i] = ((5 - i) * a0 + i * a1) // 5
                    pal_a[6], pal_a[7] = 0, 255
                cbase = 8
            else:
                raw_a, pal_a, cbase = 0, [255] * 8, 0
            c0, c1 = struct.unpack_from('<HH', blk, cbase)
            bits = struct.unpack_from('<I', blk, cbase + 4)[0]
            cols = [(((c >> 11) & 0x1F) * 255 // 31,
                     ((c >> 5) & 0x3F) * 255 // 63,
                     (c & 0x1F) * 255 // 31) for c in (c0, c1)]
            if c0 > c1:
                c2 = tuple((2 * cols[0][i] + cols[1][i]) // 3 for i in range(3))
                c3 = tuple((cols[0][i] + 2 * cols[1][i]) // 3 for i in range(3))
            else:
                c2 = tuple((cols[0][i] + cols[1][i]) // 2 for i in range(3))
                c3 = (0, 0, 0)
            pal = [cols[0], cols[1], c2, c3]
            for py in range(4):
                y = by * 4 + py
                if y >= h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= w:
                        continue
                    n = 4 * py + px
                    r, g, b = pal[(bits >> (2 * n)) & 3]
                    o = (y * w + x) * 4
                    out[o], out[o + 1], out[o + 2] = r, g, b
                    out[o + 3] = pal_a[(raw_a >> (3 * n)) & 7]
            pos += block
    return Image.frombytes('RGBA', (w, h), bytes(out))


CACHE = {}


def tex(key, size):
    if key not in CACHE:
        p = find(key)
        if p is None:
            return None
        CACHE[key] = dds_image(p)
    img = CACHE[key]
    if img is None:
        return None
    w, h = size
    return img.resize((max(1, w), max(1, h)), Image.BILINEAR)


# ------------------------------------------------------------------- render
def additive(base, layer, alpha):
    """Additively blend `layer` onto `base` scaled by alpha (0..1)."""
    if alpha >= 0.999:
        scaled = layer
    else:
        scaled = layer.point(lambda v: int(v * alpha))
    return ImageChops.add(base, scaled)


def render(panel, patched, size=(640, 800)):
    W, H = size
    canvas = Image.new('RGBA', (W, H), (14, 12, 18, 255))

    # dark background with a hint of ground so the screen fill is visible
    d = ImageDraw.Draw(canvas)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(22 + 18 * t), int(20 + 14 * t),
                                       int(24 + 12 * t), 255))

    if patched:
        tile_key, grad_key, fill_a, edge_a, scale = 'swirls', 'grad_old', 0.05, 0.90, 1.0
    else:
        tile_key, grad_key, fill_a, edge_a, scale = 'tile_new', 'grad_new', 0.16, 1.00, 1.25

    # 1) tile / fill texture ------------------------------------------------
    tile = tex(tile_key, (W, H))
    if tile is not None:
        # tile the texture across the frame, the way the engine does
        tiled = Image.new('RGBA', (W, H))
        tw, th = max(64, int(W / 1.5)), max(64, int(H / 1.5))
        piece = tex(tile_key, (tw, th))
        for y in range(0, H, th):
            for x in range(0, W, tw):
                tiled.paste(piece, (x, y))
        if scale != 1.0:
            tiled = tiled.point(lambda v: min(255, int(v * scale)))
        canvas = additive(canvas, tiled, fill_a)

    # 2) gradient / membrane ------------------------------------------------
    grad = tex(grad_key, (W, H))
    if grad is not None:
        if scale != 1.0:
            grad = grad.point(lambda v: min(255, int(v * scale)))
        canvas = additive(canvas, grad, edge_a * 0.8)

    # 3) particles ----------------------------------------------------------
    part = tex('part_new', (128, 128))
    if part is not None:
        count = 90 if not patched else 90
        pcanvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        pa = 0.45 if not patched else 0.30
        for _ in range(count):
            s = random.randint(40, 150) if not patched else random.randint(30, 110)
            x = random.randint(-40, W - 20)
            y = random.randint(-40, H - 20)
            p = part.resize((s, s), Image.BILINEAR)
            pcanvas.alpha_composite(p, (x, y))
        if pa < 0.999:
            pcanvas = pcanvas.point(lambda v: int(v * pa))
        canvas = additive(canvas, pcanvas, 1.0)

    return canvas.convert('RGB')


def label(img, text, sub):
    W, H = img.size
    band = 56
    out = Image.new('RGB', (W, H + band), (10, 10, 14))
    out.paste(img, (0, band))
    d = ImageDraw.Draw(out)
    try:
        f1 = ImageFont.truetype('segoeui.ttf', 24)
        f2 = ImageFont.truetype('segoeui.ttf', 16)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    d.text((12, 8), text, fill=(255, 255, 255), font=f1)
    d.text((12, 34), sub, fill=(170, 180, 200), font=f2)
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    before = render(None, patched=False)
    after = render(None, patched=True)

    b = label(before, 'BEFORE  (current)', 'ShockTile01 + ShockParticles02 + GradShockHit')
    a = label(after, 'AFTER  (patched)', 'DarkSwirls + ShockParticles02 + GradShockEnchArmor')

    combo = Image.new('RGB', (b.width + a.width + 12, max(b.height, a.height)),
                      (10, 10, 14))
    combo.paste(b, (0, 0))
    combo.paste(a, (b.width + 12, 0))
    combo.save(os.path.join(OUT, 'before-after.png'))
    b.save(os.path.join(OUT, 'before.png'))
    a.save(os.path.join(OUT, 'after.png'))
    print('written:', os.path.join(OUT, 'before-after.png'))
