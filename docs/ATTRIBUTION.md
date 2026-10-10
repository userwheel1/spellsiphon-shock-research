# Attribution and licensing

## This project

MIT — see [`LICENSE`](../LICENSE).

## SpellSiphon - Immersive Combat

Author: **Arctal** — https://www.nexusmods.com/skyrimspecialedition/mods/26627

No SpellSiphon assets are redistributed here. The repository reads
`Spellsiphon.esp` at runtime to analyse it; nothing from it is copied into the
released mod. SpellSiphon remains the property of its author, and this project is
an independent, user-side fix.

## The textures shipped in the mod

The released mod redistributes modified derivatives of vanilla Skyrim textures:

```text
textures\effects\ShockTile01.dds
textures\effects\ShockParticles02.dds
textures\effects\Gradients\GradShockHit.dds
```

Source: `Skyrim - Textures5.bsa` from **The Elder Scrolls V: Skyrim Special
Edition**, © Bethesda Softworks.

Only one channel is modified — the alpha — and it is scaled down, never
replaced with new artwork. The underlying colour data is vanilla. If you are
uncomfortable redistributing derivatives of Bethesda textures, rebuild the set
locally from your own game files:

```bash
python tools/build_no_aura.py
```

## Inspiration / prior work

**Spellsiphon Patch - Reduced Life Draw Lightning Visual** (Nexus 179927)

The author of that patch described swapping the Woven Power / draw effect shader
for vanilla `AlchArmorShockFXS`, and it is where the shader-swap idea came from.
That mod appears to no longer be publicly available. Its approach was tested
here and did not remove the aura — the shader swap changes how the effect
composites, but the brightness comes from the textures — however, the lead was
genuinely useful and the credit is due.

**cacophony1979**

Quoted in the SpellSiphon FAQ for identifying `shockparticles02.dds` as the
problem texture, coming from Rustic Daedra. This project's measurements confirm
it: that texture is 1.9x vanilla energy in the tested modlist. The FAQ advice to
delete the replacer is correct as far as it goes, though it leaves the mod's own
impact gradient in place, which is why it only partly helps.

## Tools

**xEdit / SSEDump / BSArch** — zilav, ElminsterAU, Sheson and contributors
https://github.com/TES5Edit/TES5Edit

Used to decode plugins and archives for cross-checking, and to validate every
plugin this project builds. The EFSH field map in `tools/efsh_layout.py` was
validated field by field against xEdit's own decoded output, and the DDS files
were extracted from the game's BSA with `BSArch`.

**Pillow** — https://python-pillow.org — image handling in the Python tooling.

## Texture replacers referenced in the analysis

Measured, not redistributed. Their presence in the test modlist is what made the
brightness difference visible:

- **Voltage** — Nexus 15565 — shock texture replacer
- **RUSTIC DAEDRA SSE** — source of the 1.9x `ShockParticles02.dds`
- **Particle Patch for ENB** — supplies `DarkSwirls.dds`
- **Inferno - Fire Effects Redux** — also supplies `DarkSwirls.dds`

## The tested modlist

Analysis was performed against the **Merethic** modlist
(Skyrim SE, Mod Organizer 2), SpellSiphon 5.28. The modlist itself is not part
of this project and no modlist files are redistributed.
