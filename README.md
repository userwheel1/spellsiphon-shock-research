# Spellsiphon — Shock Visual Research

Reverse-engineering notes and tooling for **Spellsiphon - Immersive Combat**
(Skyrim Special Edition, Nexus 26627), plus the texture mod that came out of it.

The goal was to remove the static electricity that flickers around the character
while **Woven Power** accumulates — it builds up until it covers half the screen.

**Result: solved.** The aura is drawn by two textures, and it survives as long as
any opacity remains. Zeroing their alpha removes it.

```text
ShockTile01.dds        alpha -> 0.00     the tile fill
ShockParticles02.dds   alpha -> 0.00     the spark particles
GradShockHit.dds       alpha -> 0.35     kept deliberately faint
```

The gradient is retained so the remaining electric effects — the Life draw on
the hand in particular — still read as electricity instead of exposing bare
geometry.

---

## The mod

`dist-nexus/Spellsiphon - No Static Aura.zip` — texture-only, no plugin, no
mechanics changed.

Validated in Mod Organizer 2 against Voltage, RUSTIC DAEDRA SSE and Particle
Patch for ENB.

## Why this repository may still be useful

Getting to that two-file answer took a long and mostly wrong path. Several
plausible hypotheses were tested and disproved, and the tools and format notes
below exist because of it:

- a complete **EFSH `DATA` field map** (100 fields), cross-checked against
  xEdit's own decode
- the **VMAD v5 object-reference encoding**, which is not documented clearly
  anywhere and cost hours to pin down
- a **DDS codec** in pure Python covering DXT1/3/5, DX10 BC1–BC7, BC4/BC5 and
  uncompressed 32-bit, plus a writer
- the **plugin container rules** for a valid override plugin, learned by having
  a build rejected twice

See [`docs/RESEARCH-NOTES.md`](docs/RESEARCH-NOTES.md) for the findings and the
dead ends, and [`docs/TOOLS.md`](docs/TOOLS.md) for what each script does.

## Layout

```text
tools/            the tooling (35 Python modules)
docs/             research notes, tool index, attribution, publication material
dist-nexus/       the release archive
dist-tex/         texture build variants (light / medium / strong / no-aura)
dist-effect/      plugin experiments (superseded, kept for reference)
```

## Reproducing

```bash
# EFSH DATA layout is self-checking: asserts 100 fields covering 400 bytes
python tools/efsh_layout.py

# re-validate that layout against xEdit's decoded output
python tools/validate_layout.py

# decode any DDS and prove the codec round-trips exactly
python tools/ddsio.py /tmp

# measure how bright the shock textures installed in a modlist really are
python tools/compare_textures.py

# rebuild the released texture set
python tools/build_no_aura.py
python tools/package_nexus.py
```

## Configuration

No path is hardcoded. Everything resolves through `tools/config.py`, which reads
environment variables and falls back to a conventional mod-manager layout:

```text
<MODLIST_ROOT>/mods/<mod name>/...
<MODLIST_ROOT>/Stock Game/Data/Skyrim.esm
<MODLIST_ROOT>/tools/xEdit/BSArch64.exe
```

Set `MODLIST_ROOT` and the rest follows:

```bash
# Windows
set MODLIST_ROOT=D:\Games\MyList
# POSIX
export MODLIST_ROOT=/games/MyList
```

Individual paths can be overridden when the layout differs:

| Variable | Default |
|---|---|
| `MODLIST_ROOT` | current working directory |
| `SPELLSIPHON_ESP` | `<root>/mods/Spellsiphon - Immersive Combat/Spellsiphon.esp` |
| `SKYRIM_ESM` | `<root>/Stock Game/Data/Skyrim.esm` |
| `MODS_DIR` | `<root>/mods` |
| `BSARCH` | `<root>/tools/xEdit/BSArch64.exe` |
| `VANILLA_TEX_DIR` | `<root>/research/bsa_extract/Skyrim - Textures5` |
| `RESEARCH_DIR` | `<root>/research` |

To see what actually resolved — and which of it is missing:

```bash
python tools/config.py
```

## Requirements

- Python 3.12 with Pillow
- Skyrim SE game files, and SpellSiphon installed, for anything that reads the
  plugin or the vanilla textures
- xEdit (`SSEDump`) is optional but recommended — several tools cross-check
  against its decoded output

## Verification

Every claim in `docs/RESEARCH-NOTES.md` was verified one of two ways: by parsing
the binary files directly, or by cross-checking against xEdit 4.1.5f's own
decode. The EFSH layout validation covers 115 field comparisons across two
records with zero mismatches.

## Credits

- **Arctal** — author of Spellsiphon - Immersive Combat
- The author of *Spellsiphon Patch - Reduced Life Draw Lightning Visual*
  (Nexus 179927), whose description pointed at the effect-shader path
- **zilav, ElminsterAU, Sheson** and the xEdit team — `SSEDump` and `BSArch`
- **cacophony1979**, whose texture diagnosis is quoted in the SpellSiphon FAQ

## Publishing

The release archive under `dist-nexus/` is the Nexus upload; its README is
`docs/README-no-static-aura.txt`, and `tools/package_nexus.py` packs the two
together and asserts that no plugin sneaks in.

Release notes are the `1.0.0 — release` section of
[`CHANGELOG.md`](CHANGELOG.md).

Repository description and topics:

```text
Reverse-engineering notes and tooling for Spellsiphon's shock visuals, plus a
texture-only fix that removes the static aura around the character while Woven
Power accumulates.
```

```text
skyrim skyrim-special-edition skyrimse modding xedit reverse-engineering tes5 spellsiphon
```

## Licence

MIT, for the code — see [LICENSE](LICENSE).

The MIT grant covers the Python tooling. It does **not** and cannot cover the
`.dds` files: those are alpha-scaled derivatives of vanilla textures from
`Skyrim - Textures5.bsa`, and Skyrim assets remain the property of Bethesda
Softworks. See [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) for the full
breakdown, including what is redistributed and how to rebuild the textures from
your own game files instead.
