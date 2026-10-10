# Changelog

## 1.0.0 — release

### The fix

**Spellsiphon - No Static Aura** — a texture-only replacement that removes the
static electricity building up around the character as Woven Power accumulates.

```text
ShockTile01.dds        alpha -> 0.00
ShockParticles02.dds   alpha -> 0.00
GradShockHit.dds       alpha -> 0.35   (kept deliberately faint)
```

No plugin. No mechanics changed. Confirmed working in the Merethic modlist.

### What it took to get there

Four hypotheses were tested and disproved before the texture answer:

1. **Effect Shader records.** Replacing `KSSC_ShockShader` (`0403603E`) with
   vanilla `AlchArmorShockFXS` — the approach the Nexus 179927 patch describes —
   did not change the aura.
2. **All ten shock shaders.** A patch covering every EFSH built from the same
   texture recipe also had no visible effect.
3. **The Woven Power script property.** Clearing
   `KSSC_WovenPowerVisualME.kssc_playeffectduring.EffectsToPlay` (the vanilla
   dragon-resurrection streaks effect) also did not change the aura.
4. **Graded texture dimming.** An 82% energy reduction helped but did not remove
   it.

The decisive test: fully transparent versions of the shock textures removed the
aura completely. That proved it is texture-driven and that it survives as long
as any opacity remains — so the alpha has to reach zero, not merely drop.

It also showed why partial clearing is unattractive: with `ShockTile01`
transparent, the draw effect on the hand exposes flat 2-D quads. The release
therefore keeps the gradient at 35%.

### Added

- `tools/ddsio.py` — DDS codec (DXT1/3/5, DX10 BC1–BC7, BC4/BC5, uncompressed)
  with a round-trip self-test, and a writer.
- `tools/efsh_layout.py` — the 400-byte EFSH `DATA` field map, 100 fields,
  self-checking.
- `tools/validate_layout.py` — validates that map against xDump output
  (115 comparisons, zero mismatches).
- `tools/compare_textures.py` — extracts vanilla textures from the game BSA and
  measures them against every installed replacer.
- `tools/build_visual_map.py` — map of all ~318 visual references in
  SpellSiphon, built from xDump's authoritative decode.
- `tools/build_no_aura.py`, `tools/package_nexus.py` — build and package the
  release.
- `tools/make_blank_test.py` — the transparent-texture decision test.
- `tools/check_installed.py` — reports what is actually installed in a modlist.
- `docs/RESEARCH-NOTES.md` — the findings, including the dead ends, plus format
  notes for EFSH `DATA`, VMAD v5 object references, plugin container rules and
  DDS blocks.
- `docs/TOOLS.md`, `docs/ATTRIBUTION.md`, `tools/check_history.py` — a scan that
  proves the repository history carries no personal paths and no stray files.

### Verified

- EFSH `DATA` layout: 115 field comparisons against xEdit's decode, zero
  mismatches.
- DDS codec: 2048/2048 pixels identical on raw round-trip.
- Both hand-built plugins: `SSEDump -check -dcr` reports no errors.
- The Woven Power plugin: `EffectsToPlay` empty, all other subrecords
  byte-identical, `DATA` untouched.
- Release archive: contains no `.esp` / `.esm` / `.esl`, asserted at package
  time.

### Known limitations

- The mechanism behind the aura is measured but not fully explained: which
  record applies the shock textures to the player continuously is still open.
  SpellSiphon applies shaders from scripts at runtime, so the link is not always
  visible as a static record reference. See section 5 of the research notes.
- The graded variants (`light` / `medium` / `strong`) are kept for reference.
  None of them removes the aura; only the zero-alpha set does.
- The plugin experiments in `dist-effect/` are superseded. They are shipped for
  documentation value only.

### Retired

Earlier work under the name **Spellsiphon - Subtle Draw Effects**, and the
plugin **Spellsiphon - No Draw Lightning**, are superseded. Both names described
hypotheses that turned out to be wrong — the aura is not a Draw effect, and no
plugin can remove it.
