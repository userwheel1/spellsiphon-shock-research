#!/usr/bin/env python3
"""
package_variants.py - turn the built plugins into Mod Organizer 2 ready packages.

For every variant directory under dist/, writes:
    Spellsiphon - Subtle Draw Effects.esp    (built by build_patch.py)
    meta.ini                                 (Mod Organizer 2 metadata)
    README.txt                               (short install note, RU + EN)

Creating a meta.ini keeps Mod Organizer from treating the folder as an
unmanaged/foreign mod.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DIST = os.path.join(PROJECT, 'dist')

PLUGIN_NAME = 'Spellsiphon - Subtle Draw Effects'
SITE = 'Extracted from the Spellsiphon - Subtle Draw Effects project'
VERSION = '1.0.0'
NEXUS_MODID = '0'          # set once published
NEXUS_FILEID = '0'

README = """Spellsiphon - Subtle Draw Effects
=================================

{VARIANT_TITLE}

WHAT THIS IS
------------
An override plugin for "Spellsiphon - Immersive Combat" (Nexus 26627).
It replaces one Effect Shader record - KSSC_ShockShader - which is the
view shader SpellSiphon applies while you draw the Life (shock) element.
That shader is what builds up and covers the screen during Woven Power
rotations, especially in first person.

Nothing else is touched. An Effect Shader holds only texture paths and
particle/emission parameters, so Woven Power accumulation, damage,
cooldowns, attunement and every other mechanic stay exactly as before.

INSTALL (Mod Organizer 2)
-------------------------
1. Put this folder into your modlist's "mods" directory, or use
   "Install a new mod from an archive" and point MO2 at a zip of it.
2. Enable it in the left pane.
3. Make sure the plugin is enabled in the right pane and sorts AFTER
   Spellsiphon.esp. With default sorting it will, because the file name
   starts with "Spellsiphon - S" and sorts after "Spellsiphon.esp".
4. Start the game.

No ESP cleaning or merging is needed. Load order does not matter beyond
"after Spellsiphon.esp".

UNINSTALL
---------
Disable the mod in MO2. SpellSiphon is never modified, so removing this
patch restores the original visuals exactly.

REQUIREMENTS
------------
* Skyrim Special Edition / Anniversary Edition
* Spellsiphon - Immersive Combat (Nexus 26627) - developed and verified
  against version 5.28 (Complete Edition)

NOTES
-----
An override plugin for Spellsiphon - Immersive Combat. It replaces one Effect
Shader record (KSSC_ShockShader), which drives the glow while drawing the Life
element. No SpellSiphon mechanic is changed.

Install: drop the folder into your mod manager's mods directory, or install the
archive through Mod Organizer 2, enable it and make sure the plugin sorts AFTER
Spellsiphon.esp. Nothing else is required.

Uninstall: disable the mod. SpellSiphon's own files are never modified.

Requirements: Skyrim SE/AE and Spellsiphon 5.28 (the version this was built and
tested against).
""".replace('{VARIANT_TITLE}', '{variant_title}')

VARIANT_TITLES = {
    'All Life + Switch': (
        'Variant: All Life + Switch  (broadest safe set)\n'
        'Overrides 17 Effect Shader records: every Life-element shader plus the\n'
        'weapon/spell switching shaders. SpellSiphon builds almost all of its\n'
        'lightning visuals from one recipe (ShockTile01.dds + ShockParticles02.dds\n'
        '+ the very bright GradShockHit.dds gradient), so patching a single record\n'
        'leaves the rest glowing.\n'
        '\n'
        'Includes KSSC_WeaponSwitchShader - the brightest record in the mod\n'
        '(Color Scale 4.0, Color Key 2 pure white 255,255,255) - which is the\n'
        'prime suspect for a white screen fill.\n'
        '\n'
        'Use this if the Draw-only patch did not solve the problem.'
    ),
    'All Life Shaders': (
        'Variant: All Life Shaders\n'
        'Overrides 8 Effect Shader records for the Life (shock) element only:\n'
        'Draw, Life Discharge, Elemental Overload, Life Focus, weapon imbue,\n'
        'bound-weapon attunement, imbue burst and Life Cage.\n'
        '\n'
        'These are the shaders that stay applied while Life is drawn or imbued,\n'
        'so together they produce the persistent electrification that builds up\n'
        'with Woven Power. Weapon and spell switching visuals are left alone.'
    ),
    'Both Shaders': (
        'Variant: Both Shaders\n'
        'Overrides the two shock shaders the (hidden) Nexus patch 179927\n'
        'addressed: KSSC_ShockShader and KSSC_ShockShader_Silent.\n'
        '\n'
        'This was an early attempt. It covers Draw plus Life Discharge / Life\n'
        'Cage, but not the weapon imbue or switch visuals. Prefer the\n'
        '"All Life Shaders" or "All Life + Switch" variant.'
    ),
    'Vanilla Shock': (
        'Variant: Vanilla Shock\n'
        'Overrides only the Draw shader (KSSC_ShockShader) with the vanilla\n'
        'Effect Shader AlchArmorShockFXS. This is the edit the Nexus patch\n'
        '"Spellsiphon Patch - Reduced Life Draw Lightning Visual" (179927)\n'
        'describes.\n'
        '\n'
        'Known limitation: it does NOT stop the electrification that builds up\n'
        'from stacking Woven Power, because the persistent Life shaders\n'
        '(weapon imbue, bound-weapon attunement, overload, life focus) are\n'
        'separate records. Kept for reference.'
    ),
    'Minimal': (
        'Variant: Minimal\n'
        'Keeps SpellSiphon\'s own emission/particle tuning and changes only the\n'
        'two subrecords that cause the over-bright look on the Draw shader:\n'
        '    ICON : Effects\\ShockTile01.dds  ->  Effects\\DarkSwirls.dds\n'
        '    NAM8 : Effects\\Gradients\\GradShockHit.dds\n'
        '           ->  Effects\\Gradients\\GradShockEnchArmor.dds'
    ),
    'Mage Glow': (
        'Variant: Mage Glow\n'
        'Replaces the Draw shader with vanilla MagicArmorOakFleshFXS\n'
        '(Skyrim.esm 00094160): a low-key generic spell glow with no shock\n'
        'texture at all.'
    ),
}


def main() -> int:
    if not os.path.isdir(DIST):
        print(f'no dist directory: {DIST}')
        return 1

    count = 0
    for name in sorted(os.listdir(DIST)):
        folder = os.path.join(DIST, name)
        if not os.path.isdir(folder):
            continue
        plugin = os.path.join(folder, PLUGIN_NAME + '.esp')
        if not os.path.isfile(plugin):
            print(f'skip (no plugin): {name}')
            continue

        match = re.search(r'\(([^)]+)\)\s*$', name)
        variant = match.group(1) if match else name
        title = VARIANT_TITLES.get(variant, f'Variant: {variant}')

        with open(os.path.join(folder, 'README.txt'), 'w', encoding='utf-8') as fh:
            fh.write(README.format(variant_title=title))

        meta = (
            '[General]\n'
            f'gameName=Skyrim Special Edition\n'
            f'modid={NEXUS_MODID}\n'
            f'fileid={NEXUS_FILEID}\n'
            f'version={VERSION}\n'
            f'url=\n'
            f'installationFile=\n'
            f'comments=\n'
            f'notes=Override for Spellsiphon.esp EFSH KSSC_ShockShader (0403603E). '
            f'Variant: {variant}.\n'
            f'site={SITE}\n'
        )
        with open(os.path.join(folder, 'meta.ini'), 'w', encoding='utf-8') as fh:
            fh.write(meta)

        print(f'packaged: {name}')
        count += 1

    print(f'\n{count} package(s) prepared in {DIST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
