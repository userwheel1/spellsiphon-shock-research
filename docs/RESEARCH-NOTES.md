# Research notes

Everything below was verified against the actual files: `Spellsiphon.esp`
(5.28), `Skyrim.esm`, and the installed texture replacers. Where a claim came
from xEdit rather than my own parser, that is stated.

Versions used: SpellSiphon **Complete Edition 5.28** (archive
`Spellsiphon - Complete Edition-26627-5-28-1719216785.7z`, plugin dated
2024-06-24), xEdit **4.1.5f**.

---

## 1. The answer, first

The static electricity that builds up around the character with Woven Power is
drawn by **these textures**, not by a shader record, a script property or a mesh:

| Texture | Role |
|---|---|
| `textures\effects\ShockTile01.dds` | `ICON` — tile fill, the main source of the arcs |
| `textures\effects\ShockParticles02.dds` | `ICO2` — spark particles |
| `textures\effects\Gradients\GradShockHit.dds` | `NAM8` — impact gradient |

Critical detail: **it survives as long as any opacity remains.** An 82% energy
reduction did not remove it. Only a zero alpha on the tile and particle textures
did. The gradient can stay faint — 35% keeps the remaining electric visuals
readable instead of exposing bare geometry.

---

## 2. Dead ends worth documenting

Four hypotheses were tested and disproved before the texture answer. Recording
them here is the point of this repository.

### 2.1 Effect Shader records

`EFSH KSSC_ShockShader` (`0403603E`) is the shader referenced by the
`DrawShaders` script property of `MGEF KSSC_DrawME` (`04002857`) and
`MGEF KSSC_DrawDeathME` (`04002859`). Replacing its whole `DATA` payload with
vanilla `AlchArmorShockFXS` (`Skyrim.esm 0010BEAC`) **did not change the aura**.

There are ten shaders in SpellSiphon built from the same recipe
(`ShockTile01` + `ShockParticles02` + `GradShockHit`), and a patch covering all
of them also did not change the aura:

```text
KSSC_ShockShader                     0403603E   Draw
KSSC_ShockShader_Silent              044459F1   Life Discharge, Life Cage
KSSC_OverloadFX_Life_Shader          04911CE5   Elemental Overload
KSSC_BoundSoulfoci_Shader            0496CF20   Life Focus
KSSC_WeaponEnchantmentShader_Life    042D9C4A   weapon imbue
KSSC_BoundWeaponAttunementShader_Life 04427EAC  bound weapon
KSSC_WeaponEnchantShader_Burst_Life  0457B033
KSSC_LifeCageShader                  046E4E1B
KSSC_WeaponSwitchShader              045DBB09   colour scale 4.0, white
KSSC_WhiteCracksShader               0474F355   unreferenced in the plugin
```

Why that patch failed is instructive: overriding shader *parameters* changes how
the shader composites, but the brightness that actually matters here comes from
the texture pixels. A parameter change on an unchanged bright texture looks
identical in practice.

### 2.2 The Woven Power script property

`MGEF KSSC_WovenPowerVisualME` (`042B4A2C`) is the only record that references
the vanilla dragon-resurrection streaks effect
`RFCT 000CEE0E <FXDragonResurStreaksEffect>`, through
`kssc_playeffectduring.EffectsToPlay`. Clearing that array (built, verified,
shipped as `dist-effect/`) also **did not change the aura**.

That does not mean the property is useless — it removes the dragon streaks — it
simply is not what makes the flickering static.

### 2.3 Mesh geometry

The Woven Power explosion is `EXPL 04504369 <KSSC_WovenPowerExplosion>` with mesh
`Magic\ExplosionIllusionLight01.nif`. Ruled out by the transparency test below.

### 2.4 The decision test

Transparent (alpha = 0) versions of just the three shock textures removed the
aura **completely**. Two conclusions follow immediately:

1. the aura is texture-driven, so no record or script edit can remove it;
2. partial dimming cannot remove it, so the alpha has to reach zero.

The same test also produced a useful artefact: with `ShockTile01` fully
transparent, the draw effect on the hand showed **flat 2-D quads** — the
shader's geometry, normally covered by the texture. This is why the released
mod keeps `GradShockHit` at 35% rather than clearing everything.

---

## 3. Textures: how much brighter the replacers were

`energy = luminance x alpha` — how much light the layer actually contributes.
Measured on the decoded textures.

| Texture | Vanilla | Installed | Replacer | Ratio |
|---|---|---|---|---|
| `ShockTile01.dds` | 41.9 | 26.8 | Voltage | 0.64x |
| `ShockParticles02.dds` | 6.7 | 12.5 | **RUSTIC DAEDRA SSE** | **1.9x** |
| `GradShockHit.dds` | 21.8 | 28.0 | Voltage | 1.3x |
| `DarkSwirls.dds` | 17.6 | 37.0 | Particle Patch for ENB | 2.1x |

`ShockParticles02.dds` at 1.9x vanilla matches the diagnosis quoted in the
SpellSiphon FAQ (cacophony1979: *"the texture in question is shockparticles02.dds
and it was coming from Rustic Daedra"*). That advice is correct as far as it
goes, but deleting a replacer still leaves the mod's own impact gradient in
place, which is why it only partly helps.

Also worth noting for anyone editing shaders: routing a shader to
`Gradients\GradShockEnchArmor.dds` **increases** brightness, it does not reduce
it. Vanilla energy is 61.2 against 21.8 for `GradShockHit`.

---

## 4. Format notes

### 4.1 EFSH `DATA` — 400 bytes, 100 fields

The full map lives in `tools/efsh_layout.py`, verified by
`tools/validate_layout.py` against xDump's decoded values: **115 comparisons
across two records, zero mismatches.**

Layout, in field order:

```text
+0    4 packed specular bytes: R, G, B, alpha      (alpha at byte 3)
+4    Membrane Shader - Source Blend Mode          uint32
+8    Membrane Shader - Blend Operation            uint32
+12   Membrane Shader - Z Test Function            uint32
+16   Fill/Texture Effect - Color Key 1            RGB in low 3 bytes of u32
+20   Fill - Alpha Fade In Time                    float
...   Fill / Edge effect timing and alpha ratios
+84   Fill/Texture Effect - Full Alpha Ratio       float
+88   Edge Effect - Full Alpha Ratio               float
+92   Membrane Shader - Dest Blend Mode            uint32
+96   Particle Shader blend modes                  4 x uint32
+112  Particle emission block                      floats (birth, lifetime, size)
+188  Color Key 1..3 colours                       RGB (red in the LOW byte)
+200  Color Key 1..3 alphas                        float
+224  Particle rotation block                      floats
+240  Addon models, holes, texture counts          mixed
+312  Fill Color Key 2..3 colours                  RGB
+320  Fill Color Key 1..3 scale/time               floats
+344  Color Scale                                   float
+352  Particle Shader Animated                     uint32 x7
+380  Flags                                         uint32
+384  Texture Scale (U), (V)                       floats
```

Two things that cost time:

- **Colour packing is `0x00BBGGRR`** — red is the *low* byte. Decoding it as
  ARGB gives plausible-looking but wrong colours.
- The first dword is four packed colour bytes, **not** an "Unknown". For
  `AlchArmorShockFXS` it is `0x4E000000`, i.e. black with alpha 78.

### 4.2 VMAD v5 object references — 8 bytes

This is the one that caused the most damage. In `KSSC_WovenPowerVisualME`:

```text
... 00 00 ff ff | 0e ee 0c 00 ...
```

The FormID is the **second** dword, read little-endian: `0x000CEE0E`, which is
exactly `RFCT FXDragonResurStreaksEffect`. Reading the *first* dword instead
yields `0xFFFF0000`, and combinations like
`(d0 & 0xFFFF) | ((d1 & 0xFFFF) << 16)` yield `0x0EEE0C00` — a FormID that
exists nowhere, which is how the mistake was eventually caught: validate decoded
object references against the actual record lists and reject anything that does
not resolve.

Property encoding, from real bytes:

```text
<u16 strlen><name bytes>     property or script name (no NUL terminator)
<u8 type><u8 flags>          per property
<u32 count><count * 8>       object arrays; types 1, 6 and 11
```

Script headers add a `<u8 flags><u16 property count>` pair after the name. Type
`0` (None) carries **no** payload byte, which is easy to get wrong and shifts
every later read.

### 4.3 Plugin container — what xEdit accepts

Building an override plugin by hand needs all of this, and xEdit rejects the
file item by item:

1. **TES4 header order** is `HEDR`, `CNAM`, then `MAST`/`DATA` pairs. An optional
   `SNAM` (description) is a good place to record the patch version, since every
   variant tends to ship under the same plugin filename.
2. TES4 is 24 bytes: signature, data size, flags, form id, version control info,
   form version (44 for SSE), then two bytes of padding.
3. **Records must be wrapped in a `GRUP`.** A bare top-level record is rejected
   as *"invalid top level record"*.
4. For a top-level type group the **group type is 0 and the label is the record
   signature** (`EFSH`, `MGEF`). Using the FormID as the label gives
   *"top level group without known sort order"*.
5. GRUP header is 24 bytes: `GRUP`, total group size (including the header),
   label, group type as int32, then 8 zero bytes.

The load-order index is readable straight from a plugin's own FormIDs: a record
written as `0403603E` means the plugin sits at index `04` in the order it was
authored against. In the Merethic build `Spellsiphon.esp` is indeed the fifth
master (index 04), which confirms the mapping.

### 4.4 DDS

`tools/ddsio.py` reads DXT1, DXT3, DXT5, DX10 BC1/BC2/BC3/BC4/BC5/BC7 and
uncompressed formats with arbitrary channel masks, and writes uncompressed
32-bit BGRA. It has a self-test:

```bash
python tools/ddsio.py /tmp      # -> raw round-trip: 2048/2048 pixels identical
```

The DXT5 block layout is worth stating because getting it backwards produces
plausible garbage: 8 bytes of alpha (2 endpoints plus 48 bits of 3-bit indices)
followed by 8 bytes of colour (2 x RGB565 plus 32 bits of 2-bit indices).

---

## 5. Where the aura actually comes from — open question

The measuring is done, but the mechanism is not fully pinned down. What is
certain:

- it is texture-driven (proven by the transparency test);
- it is not any of the ten EFSH records in the plugin, and not the Woven Power
  `EffectsToPlay` property.

What is *not* established: which record applies a shader that reads
`ShockTile01` / `ShockParticles02` to the player continuously. SpellSiphon
applies shaders from scripts at runtime, so the link is not always visible as a
static record reference. A useful next step would be to hook the shader
application calls in game, or to bisect by clearing textures one at a time.

For the purpose of removing the effect this is academic — the texture fix is
complete and small.

---

## 6. Names that mislead

- The FAQ's suggested replacement shader is remembered there as
  *"AlchMagicArmor (iirc)"*. **No such record exists.** The real one is
  `AlchArmorShockFXS` (`0010BEAC`). The `MagicArmor*FXS` records
  (`00094160`–`00094163`, `000E9AC8`) are the Oakflesh/Stoneflesh/Ironflesh/
  Ebonyflesh/Dragonhide family and are unrelated.
- `KSSC_WhiteCracksShader` (`0474F355`) is referenced by **nothing** in
  `Spellsiphon.esp`. It looks like a leftover.
- The vanilla streak effect SpellSiphon plays for Woven Power is
  `FXDragonResurStreaksEffect` — literally the visual used by Alduin's
  resurrection, not a bespoke electric effect.
