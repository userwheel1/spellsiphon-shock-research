"""Verify the built effect patch: the record must be an override of
KSSC_WovenPowerVisualME whose EffectsToPlay array is empty, with everything else
byte-identical to the original.
"""
import os
import struct
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

PATCH = os.path.join(PROJECT, 'dist-effect',
                     'Spellsiphon - No Woven Power Lightning',
                     'Spellsiphon - No Woven Power Lightning.esp')
SS = SPELLSIPHON_ESP
TARGET = 0x042B4A2C


def read(p):
    with open(p, 'rb') as f:
        return f.read()


def recs(b):
    o, n = 0, len(b)
    while o + 24 <= n:
        s = b[o:o + 4]
        sz = struct.unpack_from('<I', b, o + 4)[0]
        if s == b'GRUP':
            o += 24
            continue
        if o + 24 + sz > n:
            break
        yield o, s, sz, struct.unpack_from('<I', b, o + 12)[0]
        o += 24 + sz


def subs(b, ro, sz):
    o, e = ro + 24, ro + 24 + sz
    while o + 6 <= e:
        st = b[o:o + 4]
        sl = struct.unpack_from('<H', b, o + 4)[0]
        o += 6
        yield st, b[o:o + sl]
        o += sl


def get_subs(path, fid):
    b = read(path)
    for off, sig, size, f in recs(b):
        if f == fid:
            return {s: p for s, p in subs(b, off, size)}
    return None


patch = get_subs(PATCH, TARGET)
orig = get_subs(SS, TARGET)

ok = True


def check(cond, label, detail=''):
    global ok
    if not cond:
        ok = False
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f'  ({detail})' if detail else ''))


print(f'patch : {PATCH}')
print(f'  size {os.path.getsize(PATCH)} bytes\n')
check(patch is not None, 'patch contains the target record')
if patch is None:
    sys.exit(1)

print('subrecords compared against the original:')
for sig in orig:
    same = patch.get(sig) == orig[sig]
    tag = 'identical' if same else 'CHANGED'
    print(f'  {sig.decode():<5} {len(orig[sig]):>4} -> {len(patch.get(sig, b"")):>4} bytes   {tag}')
    if sig != b'VMAD':
        check(same, f'{sig.decode()} unchanged')

# VMAD: the EffectsToPlay array must be empty, everything else intact
vmad = patch[b'VMAD']
ovmad = orig[b'VMAD']
check(len(vmad) == len(ovmad) - 8, 'VMAD shrank by exactly one 8-byte object',
      f'{len(ovmad)} -> {len(vmad)}')

i = vmad.find(b'EffectsToPlay')
check(i >= 0, 'EffectsToPlay property present')
if i >= 0:
    cnt = struct.unpack_from('<I', vmad, i + 15)[0]
    check(cnt == 0, 'EffectsToPlay array is empty', f'count={cnt}')

j = ovmad.find(b'EffectsToPlay')
if j >= 0:
    before = struct.unpack_from('<I', ovmad, j + 15)[0]
    fid = struct.unpack_from('<I', ovmad, j + 19 + 4)[0]
    names = {0x0CEE0E: 'RFCT FXDragonResurStreaksEffect'}
    check(fid == 0x0CEE0E, 'the removed object is the dragon-resurrection streaks effect',
          f'0x{fid:08X} {names.get(fid, "")}')

# everything else must still be there: other script properties preserved
for needle in (b'EffectDuration', b'InitialSoundToPlay', b'ExplosionToPlace',
               b'kssc_playsoundduring', b'kssc_explosionattarget'):
    check(needle in vmad, f'{needle.decode()} preserved')

check(patch[b'DATA'] == orig[b'DATA'], 'MGEF DATA (gameplay fields) unchanged')
check(patch[b'EDID'] == orig[b'EDID'], 'EditorID unchanged')

print('\n' + ('EFFECT PATCH VERIFIED' if ok else 'VERIFICATION FAILED'))
sys.exit(0 if ok else 1)
