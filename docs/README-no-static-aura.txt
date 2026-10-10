Spellsiphon - No Static Aura
============================

Removes the static electricity that flickers around the character while Woven
Power accumulates. Texture-only: no plugin, no mechanics changed.


WHAT THIS FIXES
---------------
While Woven Power stacks build up, SpellSiphon draws a shock effect around the
player that quickly covers half the screen in flickering electric arcs. This mod
removes it.


WHAT IT CHANGES
---------------
Three Effect Shader textures used by SpellSiphon's shock visuals:

    ShockTile01.dds         alpha x0.00   (the tile fill - main source of arcs)
    ShockParticles02.dds    alpha x0.00   (the spark particles)
    GradShockHit.dds        alpha x0.35   (kept faint on purpose)

The gradient is deliberately left at 35% so the remaining electric effects -
the Life draw on your hand in particular - still read as electricity instead of
exposing bare geometry.

Result: no static aura while stacking Woven Power; everything else looks normal.


WHAT IS NOT CHANGED
-------------------
Nothing but these three texture files. Specifically:

    * Woven Power accumulation, damage scaling and durations
    * All spells, shouts, perks, keywords and magic effects
    * Draw, Discharge, Life Focus, weapon imbue, bound weapons
    * Sounds
    * No plugin is installed, so there is nothing to load-order


REQUIREMENTS
------------
    * Skyrim Special Edition / Anniversary Edition
    * Spellsiphon - Immersive Combat  (developed and tested against 5.28)


INSTALL
-------
1. Install with your mod manager as usual, or copy the "textures" folder into
   your Data directory.
2. IMPORTANT: this mod must win the texture conflict. In Mod Organizer 2 place
   it BELOW (i.e. with higher priority than) any mod that also ships these
   files - commonly:
       Voltage
       RUSTIC DAEDRA SSE
       Particle Patch for ENB
   Without that, its files lose the conflict and nothing changes.
3. Start the game. Texture changes need a game launch, not a save reload.


UNINSTALL
---------
Disable or delete the mod. No original file is modified, so the default look
returns immediately.


COMPATIBILITY
-------------
* Works alongside any texture replacer, as long as it is given priority.
* Because it is purely texture-based, it is unaffected by SpellSiphon version
  changes to plugins or scripts.
* Conflicts only with mods that intentionally modify these same three textures.


CREDITS
-------
    * Arctal - author of Spellsiphon - Immersive Combat
    * Voltage, RUSTIC DAEDRA SSE and Particle Patch for ENB were used to
      identify how much brighter than vanilla the installed textures had become


HOW THIS WAS DIAGNOSED
----------------------
For anyone curious, or for a future version of SpellSiphon:

A fully transparent version of these textures removed the aura completely,
while an 82% reduction did not. That proved the aura is drawn by these textures
rather than by a shader record, a script property or a mesh, and that it
survives as long as any opacity remains - which is why zeroing the tile and
particle alpha is what actually works.

Effect Shader records, script properties (including the Woven Power
"EffectsToPlay" visual) and the supporting meshes were all tested and ruled out
beforehand.
