"""Minimal, self-contained DDS reader/writer, with a built-in round-trip test.

Supported on read:  DXT1, DXT3, DXT5 (and their DX10 BC1/2/3 equivalents),
                    uncompressed 32-bit with arbitrary channel masks.
Supported on write: uncompressed 32-bit A8R8G8B8 (the most compatible format
                    for Skyrim SE effect textures).
"""
from __future__ import annotations

import struct

from PIL import Image


# --------------------------------------------------------------------- read
def read_dds_bytes(data: bytes) -> Image.Image:
    if data[:4] != b'DDS ':
        raise ValueError('not a DDS file')
    h, w = struct.unpack_from('<II', data, 12)
    fourcc = data[84:88]
    pf_flags = struct.unpack_from('<I', data, 80)[0]
    bits = struct.unpack_from('<I', data, 88)[0]
    rmask, gmask, bmask, amask = struct.unpack_from('<IIII', data, 92)
    off = 128
    dxgi = None
    if fourcc == b'DX10':
        dxgi = struct.unpack_from('<I', data, 128)[0]
        off = 148

    dxt1 = fourcc == b'DXT1' or dxgi in (70, 71, 72)
    dxt3 = fourcc in (b'DXT3', b'DXT2') or dxgi in (73, 74, 75)
    dxt5 = fourcc in (b'DXT5', b'DXT4') or dxgi in (76, 77, 78)
    if dxt1 or dxt3 or dxt5:
        return _decode_dxt(data, off, w, h, alpha=not dxt1)
    return _decode_raw(data, off, w, h, bits, rmask, gmask, bmask, amask)


def _decode_dxt(data, off, w, h, alpha):
    block = 16 if alpha else 8
    bw, bh = (w + 3) // 4, (h + 3) // 4
    if len(data) - off < bw * bh * block:
        raise ValueError('truncated DXT data')
    out = bytearray(w * h * 4)
    pos = off
    for by in range(bh):
        for bx in range(bw):
            blk = data[pos:pos + block]
            if alpha:
                a0, a1 = blk[0], blk[1]
                araw = int.from_bytes(blk[2:8], 'little')
                pa = [a0, a1] + [0] * 6
                if a0 > a1:
                    for i in range(1, 7):
                        pa[1 + i] = ((7 - i) * a0 + i * a1) // 7
                else:
                    for i in range(1, 5):
                        pa[1 + i] = ((5 - i) * a0 + i * a1) // 5
                    pa[6], pa[7] = 0, 255
                cbase = 8
            else:
                araw, pa, cbase = 0, [255] * 8, 0
            c0, c1 = struct.unpack_from('<HH', blk, cbase)
            cbits = struct.unpack_from('<I', blk, cbase + 4)[0]
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
                    r, g, b = pal[(cbits >> (2 * n)) & 3]
                    a = pa[(araw >> (3 * n)) & 7] if alpha else 255
                    o = (y * w + x) * 4
                    out[o:o + 4] = bytes((r, g, b, a))
            pos += block
    return Image.frombytes('RGBA', (w, h), bytes(out))


def _decode_raw(data, off, w, h, bits, rmask, gmask, bmask, amask):
    step = bits // 8
    if step not in (1, 2, 3, 4):
        raise ValueError(f'unsupported bit depth {bits}')
    if len(data) - off < w * h * step:
        raise ValueError('truncated raw data')

    def shift(mask):
        if not mask:
            return None
        s = (mask & -mask).bit_length() - 1
        n = bin(mask).count('1')
        return s, n

    chans = [shift(m) for m in (rmask, gmask, bmask, amask)]
    out = bytearray(w * h * 4)
    p = off
    for i in range(w * h):
        px = int.from_bytes(data[p:p + step], 'little')
        p += step
        vals = []
        for c in chans:
            if c is None:
                vals.append(255)
            else:
                s, n = c
                v = (px & ((1 << n) - 1) << s) >> s
                vals.append((v * 255) // ((1 << n) - 1))
        out[i * 4:i * 4 + 4] = bytes(vals)
    return Image.frombytes('RGBA', (w, h), bytes(out))


def open_dds(path: str) -> Image.Image:
    with open(path, 'rb') as f:
        return read_dds_bytes(f.read())


# -------------------------------------------------------------------- write
def save_dds_bgra(img: Image.Image, path: str) -> int:
    """Write an uncompressed 32-bit A8R8G8B8 DDS (no mipmaps)."""
    img = img.convert('RGBA')
    w, h = img.size
    hdr = bytearray(b'DDS ')
    hdr += struct.pack('<I', 124)
    hdr += struct.pack('<I', 0x00000001 | 0x00000002 | 0x00000004
                       | 0x00000008 | 0x00001000)
    hdr += struct.pack('<II', h, w)
    hdr += struct.pack('<I', w * 4)
    hdr += struct.pack('<II', 0, 0)
    hdr += b'\x00' * 44
    hdr += struct.pack('<I', 32)
    hdr += struct.pack('<I', 0x1 | 0x40)
    hdr += struct.pack('<I', 0)
    hdr += struct.pack('<I', 32)
    hdr += struct.pack('<IIII', 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    hdr += struct.pack('<I', 0x1000)
    hdr += b'\x00' * 16
    assert len(hdr) == 128, len(hdr)

    body = bytearray(w * h * 4)
    for i, (r, g, b, a) in enumerate(img.getdata()):
        body[i * 4:i * 4 + 4] = bytes((b, g, r, a))

    with open(path, 'wb') as f:
        f.write(bytes(hdr))
        f.write(bytes(body))
    return 128 + len(body)


# --------------------------------------------------------------------- test
def selftest(tmpdir: str) -> bool:
    import os
    os.makedirs(tmpdir, exist_ok=True)
    ok = True
    src = Image.new('RGBA', (64, 32))
    px = src.load()
    for y in range(32):
        for x in range(64):
            px[x, y] = (x * 4 % 256, y * 8 % 256, (x + y) * 3 % 256, (x * 5 + y) % 256)
    p = os.path.join(tmpdir, 'selftest.dds')
    save_dds_bgra(src, p)
    back = open_dds(p)
    bad = sum(1 for y in range(32) for x in range(64)
              if src.getpixel((x, y)) != back.getpixel((x, y)))
    print(f'raw round-trip: {64 * 32 - bad}/{64 * 32} pixels identical')
    ok &= bad == 0
    return ok


if __name__ == '__main__':
    import sys
    sys.exit(0 if selftest(sys.argv[1] if len(sys.argv) > 1 else '.') else 1)
