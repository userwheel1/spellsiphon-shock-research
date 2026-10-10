"""Resolve the Effect Shader that KSSC_WovenPowerVisualME plays.

The 8-byte object value observed for property EffectsToPlay is
    00 00 ff ff 0e ee 0c 00
Our verified layout for VMAD v5 object values (leading dword = FormID) yields the
placeholder 0x0000FFFF, which cannot be a real record.  This tool therefore:

  1. reads the raw 8 bytes,
  2. enumerates every plausible FormID interpretation,
  3. resolves each against Spellsiphon.esp AND Skyrim.esm,
  4. reports which interpretation names a real Effect Shader.
"""
import struct
import sys
import os

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)
SS = SPELLSIPHON_ESP
SKY = SKYRIM_ESM
RAW = bytes.fromhex('0000ffff0eee0c00')


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def records(b):
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


def subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


def index(b):
    m = {}
    for off, sig, size, fid in records(b):
        edid = None
        for st, d in subs(b, off, size):
            if st == b'EDID':
                edid = d.split(b'\x00')[0].decode('utf8', 'replace'); break
        m[fid] = (sig.decode(), edid)
    return m


sp = load(SPELLSIPHON)
sky = load(SKYRIM)
m_sp = index(sp)
m_sky = index(sky)

print(f"raw object value: {RAW.hex(' ')}")
d0, d1 = struct.unpack_from('<II', RAW, 0)
u64 = struct.unpack_from('<Q', RAW, 0)[0]
print(f"  dword0=0x{d0:08X}  dword1=0x{d1:08X}  u64=0x{u64:016X}\n")

cands = {
    'dword0': d0,
    'dword1': d1,
    '(dword0 & 0xFFFF) | (dword1 << 16)': (d0 & 0xFFFF) | ((d1 & 0xFFFF) << 16),
    '(dword1 & 0xFFFF) | (dword0 << 16)': (d1 & 0xFFFF) | ((d0 & 0xFFFF) << 16),
    'u64 & 0xFFFFFFFF (low 32 of 64-bit)': u64 & 0xFFFFFFFF,
    '(u64 >> 16) & 0xFFFFFFFF': (u64 >> 16) & 0xFFFFFFFF,
    '(u64 >> 32) & 0xFFFFFFFF': (u64 >> 32) & 0xFFFFFFFF,
    'u64 bytes 2..5': int.from_bytes(RAW[2:6], 'little'),
    'u64 bytes 3..6': int.from_bytes(RAW[3:7], 'little'),
    'SWAP16 each dword': d1 << 16 | d0,
}
for label, v in cands.items():
    v &= 0xFFFFFFFF
    hit = m_sp.get(v) or m_sky.get(v)
    if hit:
        src = 'Spellsiphon.esp' if v in m_sp else 'Skyrim.esm'
        print(f"  {label:<38} 0x{v:08X}  -> {hit[0]} {hit[1]}   [{src}]")
    else:
        print(f"  {label:<38} 0x{v:08X}  -> (not found)")

print("\n=== also: what record sits at 0x0CEE0000 / 0x0CEE0000-ish? ===")
for v in (0x0CEE0000, 0x0CEE0EEE, 0x0CEEEE0C, 0x0C00000E, 0x0CEE000E):
    hit = m_sp.get(v) or m_sky.get(v)
    print(f"  0x{v:08X} -> {hit if hit else '(not found)'}")

print("\n=== Spellsiphon EFSH records (candidates for the Woven Power visual) ===")
for fid, (sig, edid) in sorted(m_sp.items()):
    if sig == 'EFSH':
        print(f"  {fid:08X}  {edid}")
