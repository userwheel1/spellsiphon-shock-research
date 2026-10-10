"""Build the authoritative visual map from xDump's own decode.

xDump already decoded every VMAD correctly, so this relies on its output rather
than re-implementing the format.  It attributes each visual reference to the
record that owns it.
"""
import os
import re
import sys

# --- shared configuration (see tools/config.py) ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (SPELLSIPHON_ESP, SKYRIM_ESM, SKYRIM_DATA,
                    MODS_DIR, BSARCH, VANILLA_TEX_DIR, RESEARCH_DIR,
                    MODLIST_ROOT)

DUMP = os.path.join(RESEARCH_DIR, 'xdump_spellsiphon.txt')

DUMPING = re.compile(r'Dumping:\s+(\w+)\s+-\s+([^\[]+)\[([0-9A-F]{8})\]\s+<([^>]*)>')
PROP = re.compile(r'Property\s+(?:\{\d+\}\s+)?#\d+\s+\[S\]:\s+([A-Za-z0-9_]+)')
VALUE = re.compile(r'Object(?:\[\])?\s*=\s*([A-Z]{4})\s+-\s+[^\[]*\[([0-9A-F]{8})\]\s*<([^>]*)>')

# property names that influence the visible effect on the player
VISUAL = re.compile(r'(fx|shader|effect|explosion|visual|vfx|imod|art|hazard|proj)',
                    re.I)


def main():
    cur = None
    rows = []
    with open(DUMP, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = DUMPING.search(line)
            if m:
                cur = (m.group(1), m.group(4).strip(), m.group(3))
                continue
            if cur is None or 'Property' not in line:
                continue
            pm = PROP.search(line)
            if not pm:
                continue
            pname = pm.group(1)
            if not VISUAL.search(pname):
                continue
            for vm in VALUE.finditer(line):
                rows.append((cur[0], cur[1], cur[2], pname,
                             vm.group(1), vm.group(2), vm.group(3)))

    # de-duplicate
    seen = set()
    uniq = []
    for r in rows:
        if r in seen:
            continue
        seen.add(r)
        uniq.append(r)

    print(f'visual-reference properties found: {len(uniq)}\n')
    for sig, edid, fid, pname, tsig, tfid, tedid in sorted(uniq, key=lambda x: (x[1], x[3])):
        print(f'  {sig:<5} {edid:<34} [{fid}]  {pname:<26} -> {tsig} {tfid} {tedid}')

    # which records touch EFSH specifically
    print('\n=== EFSH references by owning record ===')
    efsh = {}
    for sig, edid, fid, pname, tsig, tfid, tedid in uniq:
        if tsig == 'EFSH':
            efsh.setdefault((sig, edid, fid), set()).add((tedid, tfid))
    for (sig, edid, fid), shaders in sorted(efsh.items(), key=lambda x: x[0][1]):
        print(f'  {sig} {edid} [{fid}]  ({len(shaders)} shader(s))')
        for name, sfid in sorted(shaders):
            print(f'       {name} [{sfid}]')

    # the record(s) that can apply a visual to the player
    print('\n=== records whose visual properties are NOT effect shaders ===')
    for sig, edid, fid, pname, tsig, tfid, tedid in uniq:
        if tsig != 'EFSH':
            print(f'  {sig} {edid} [{fid}].{pname} -> {tsig} {tfid} {tedid}')


if __name__ == '__main__':
    main()
