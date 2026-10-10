"""Report what is actually installed in a modlist.

Prints the plugin's hash, master list, every record it overrides and the
textures it ships - so you can tell which build is currently active without
launching the game.

Usage
-----
    python tools/check_installed.py                 # uses config.py defaults
    python tools/check_installed.py path/to.esp
"""
from __future__ import annotations

import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import MODS_DIR, PATCH_ESP_NAME, PATCH_MOD_NAME

DEFAULT_ESP = os.path.join(MODS_DIR, PATCH_MOD_NAME, PATCH_ESP_NAME)


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def iter_records(b):
    off, n = 0, len(b)
    while off + 24 <= n:
        sig = b[off:off + 4]
        size = struct.unpack_from('<I', b, off + 4)[0]
        if sig == b'GRUP':
            off += 24
            continue
        if off + 24 + size > n:
            break
        yield off, sig, size, struct.unpack_from('<I', b, off + 12)[0]
        off += 24 + size


def iter_subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


def masters_of(plugin):
    size = struct.unpack_from('<I', plugin, 4)[0]
    o, end, out = 24, 24 + size, []
    while o + 6 <= end:
        sig = plugin[o:o + 4]
        sl = struct.unpack_from('<H', plugin, o + 4)[0]
        o += 6
        if sig == b'MAST':
            out.append(plugin[o:o + sl].split(b'\x00')[0].decode())
        o += sl
    return out


def main() -> int:
    esp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ESP
    if not os.path.isfile(esp):
        print(f'not found: {esp}')
        print('pass a path, or set MODLIST_ROOT / MODS_DIR (see tools/config.py)')
        return 1

    b = read(esp)
    print(f'file     : {esp}')
    print(f'size     : {len(b):,} bytes')
    print(f'sha256   : {hashlib.sha256(b).hexdigest()}')
    print(f'form ver : {struct.unpack_from("<H", b, 20)[0]}')
    print(f'masters  : {", ".join(masters_of(b))}')

    print('\nrecords:')
    count = 0
    for off, sig, size, fid in iter_records(b):
        edid = icon = nam8 = None
        for st, d in iter_subs(b, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf-8', 'replace')
            elif st == b'ICON':
                icon = d.split(b'\x00')[0].decode('utf-8', 'replace')
            elif st == b'NAM8':
                nam8 = d.split(b'\x00')[0].decode('utf-8', 'replace')
        print(f'   {sig.decode():<5} [{fid:08X}] {edid or ""}')
        if icon or nam8:
            print(f'         ICON={os.path.basename(icon or "") or "-"}  '
                  f'NAM8={os.path.basename(nam8 or "") or "-"}')
        count += 1

    tex_root = os.path.join(os.path.dirname(esp), 'textures')
    if os.path.isdir(tex_root):
        print('\ntextures:')
        for root, _d, files in os.walk(tex_root):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, os.path.dirname(esp))
                print(f'   {rel}  ({os.path.getsize(full):,} bytes)')

    print(f'\ntotal records: {count}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
