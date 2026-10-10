"""Shared path configuration.

Nothing in this repository hardcodes a user-specific location. Every path is
read from an environment variable and falls back to a conventional value, so the
tools work on any machine once the variables are set.

Environment variables
---------------------
    MODLIST_ROOT        root of the mod manager instance
                        (default: the current working directory)
    SPELLSIPHON_ESP     full path to Spellsiphon.esp
    SKYRIM_ESM          full path to Skyrim.esm
    SKYRIM_DATA         game Data directory
    MODS_DIR            directory holding installed mods
    VANILLA_TEX_DIR     where the vanilla shock textures were extracted to
    XEDIT_DIR           folder containing BSArch / SSEDump
    RESEARCH_DIR        scratch directory for generated dumps

Conventional layout assumed by the defaults:

    <MODLIST_ROOT>/mods/<mod name>/...
    <MODLIST_ROOT>/Stock Game/Data/Skyrim.esm
    <MODLIST_ROOT>/tools/xEdit/BSArch64.exe

Example
-------
    set MODLIST_ROOT=E:\\Modlists\\MyList
    python tools/compare_textures.py
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------- root
MODLIST_ROOT = os.environ.get('MODLIST_ROOT') or os.getcwd()

# ---------------------------------------------------------------- game files
SPELLSIPHON_ESP = os.environ.get('SPELLSIPHON_ESP') or os.path.join(
    MODLIST_ROOT, 'mods', 'Spellsiphon - Immersive Combat', 'Spellsiphon.esp')

SKYRIM_DATA = os.environ.get('SKYRIM_DATA') or os.path.join(
    MODLIST_ROOT, 'Stock Game', 'Data')

SKYRIM_ESM = os.environ.get('SKYRIM_ESM') or os.path.join(
    SKYRIM_DATA, 'Skyrim.esm')

MODS_DIR = os.environ.get('MODS_DIR') or os.path.join(MODLIST_ROOT, 'mods')

# ---------------------------------------------------------------- tools
XEDIT_DIR = os.environ.get('XEDIT_DIR') or os.path.join(
    MODLIST_ROOT, 'tools', 'xEdit')

BSARCH = os.environ.get('BSARCH') or os.path.join(XEDIT_DIR, 'BSArch64.exe')

# ---------------------------------------------------------------- scratch
RESEARCH_DIR = os.environ.get('RESEARCH_DIR') or os.path.join(
    MODLIST_ROOT, 'research')

VANILLA_TEX_DIR = os.environ.get('VANILLA_TEX_DIR') or os.path.join(
    RESEARCH_DIR, 'bsa_extract', 'Skyrim - Textures5')

# Name of the ShockSiphon plugin-editing mod folder used by the verification
# tools. Override if you renamed it.
PATCH_MOD_NAME = os.environ.get('PATCH_MOD_NAME') or 'Spellsiphon - No Static Aura'
PATCH_ESP_NAME = os.environ.get('PATCH_ESP_NAME') or 'Spellsiphon - No Static Aura.esp'


def describe() -> str:
    """Human-readable summary, handy when a tool cannot find something."""
    rows = [
        ('MODLIST_ROOT', MODLIST_ROOT),
        ('SPELLSIPHON_ESP', SPELLSIPHON_ESP),
        ('SKYRIM_ESM', SKYRIM_ESM),
        ('MODS_DIR', MODS_DIR),
        ('BSARCH', BSARCH),
        ('VANILLA_TEX_DIR', VANILLA_TEX_DIR),
    ]
    width = max(len(k) for k, _ in rows)
    out = ['resolved paths:']
    for k, v in rows:
        mark = '' if os.path.exists(v) else '   <- NOT FOUND'
        out.append(f'  {k:<{width}}  {v}{mark}')
    return '\n'.join(out)


if __name__ == '__main__':
    print(describe())
