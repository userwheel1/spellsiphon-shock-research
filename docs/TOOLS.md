# Tool index

35 Python modules. Everything that reads game files expects Skyrim SE and an
installed SpellSiphon; the paths can be overridden:

```bash
SPELLSIPHON_ESP=... SKYRIM_ESM=... python tools/<script>.py
```

Default paths assume the Merethic modlist layout and are set at the top of each
script.

## Core modules — the reusable parts

| Module | What it does |
|---|---|
| `ddsio.py` | DDS reader/writer. DXT1/3/5, DX10 BC1–BC7, BC4/BC5, uncompressed. `python ddsio.py <dir>` runs a round-trip self-test. |
| `efsh_layout.py` | The 400-byte EFSH `DATA` field map (100 fields). Self-checking: importing it asserts full coverage. |
| `validate_layout.py` | Re-validates that map against xDump output — 115 field comparisons. |

## Builders — produce the deliverables

| Module | What it does |
|---|---|
| `build_no_aura.py` | **Builds the released texture set.** Zeroes the tile/particle alpha. Levels: `hard`, `medium`. |
| `package_nexus.py` | Packages the release archive and asserts it contains no plugin. |
| `make_texture_fix.py` | The earlier graded variants (`light` / `medium` / `strong`) as fractions of installed energy. |
| `build_texture_variants.py` | Packages those graded variants for Mod Organizer 2. |
| `build_patch.py` | Builds the Effect Shader override plugins (`vanilla`, `minimal`, `mage`, `both`, `life`, `life-switch`). |
| `build_effect_patch.py` | Builds the plugin that clears the Woven Power `EffectsToPlay` array. Contains the byte-level VMAD surgery. |
| `package_variants.py` | Writes `meta.ini` + `README.txt` for a set of mod folders. |

## Analysis — how the conclusion was reached

| Module | What it does |
|---|---|
| `compare_textures.py` | Extracts vanilla textures from `Skyrim - Textures5.bsa` and measures vanilla vs each replacer. **This is the measurement that mattered.** |
| `measure_installed.py` | Measures the reduction actually installed in a modlist. |
| `bright_shaders.py` | Lists every EFSH whose texture set or colour scale makes it a bright "Life" shader. |
| `visual_inventory.py` | Every EFSH with its textures, key alpha/scale values, a coverage score and the records that reference it. |
| `build_visual_map.py` | Builds a map of all ~318 visual references owned by SpellSiphon records, from xDump output. |
| `all_shader_xref.py` | Cross-references every EFSH with the records that reference it. |
| `shader_xref.py` | Same for a fixed list of suspect shaders. |
| `white_shaders.py` | Compares the white/overload shader candidates. |
| `compare_variants.py` | Field-by-field comparison of the original shader against each variant. |
| `map_all_visuals.py` | Walks script properties looking for anything visual. Kept as a cautionary example: the VMAD walker in it is wrong, see `build_visual_map.py`. |

## Traces — following the effect chain

| Module | What it does |
|---|---|
| `trace_wovenpower.py` | Resolves `KSSC_WovenPowerExplosion` and `FXDragonResurStreaksEffect`. |
| `trace_attunement.py` | Follows the vanilla streaks chain and lists the attunement shaders. |
| `trace_wp_effect.py` | Traces the Woven Power effect byte pattern. |
| `find_lightning_source.py` | Finds every record whose scripts play a visual effect, and which reference the streaks effect. |
| `wpvmad3.py` | Brute-forces the VMAD object-encoding layout, validating each candidate against the real record list. This is the tool that exposed the encoding. |
| `wovenpower_chain.py` | Dumps the Woven Power / attunement chain. |
| `wp_spell.py` | Dumps the Woven Power spell and every spell referencing a Woven Power effect. |
| `resolve_wp_shader.py` | Enumerates plausible FormID interpretations of a raw 8-byte object value. |
| `resolve_explosion.py` | Resolves the Woven Power explosion record. |

## Verification

| Module | What it does |
|---|---|
| `verify_patch.py` | Structural verification of the Effect Shader patches. |
| `verify_effect_patch.py` | Verifies the Woven Power patch: array empty, everything else byte-identical. |
| `check_installed.py` | Reports what is actually installed in the modlist: hash, masters, records, textures. |
| `check_history.py` | Scans every blob reachable in the git history for personal paths, stray files and non-ASCII source. Run this before publishing. |

## Visualisation

| Module | What it does |
|---|---|
| `texture_gallery.py` | Renders the before/after texture comparison sheets in `docs/images/`. |
| `make_comparison.py` | Composites a simulated "what the shader looks like" image. Contains the DDS decode helper used by several tools. |
| `make_blank_test.py` | Builds the transparent-texture **decision test** (section 2.4 of the research notes). This is the tool that settled the question. |

## Known rough edges

- `make_comparison.py` holds a `dds_image()` helper that predates `ddsio.py`.
  New code should use `ddsio.open_dds()`. The older helper works but is slower
  and less complete.
- `map_all_visuals.py` has a broken VMAD walker (documented above). It is kept
  because the byte-level approach it tried is instructive, not because it works.
- `efsh_layout.py` maps the 400-byte SSE form of EFSH `DATA`. Records with a
  shorter payload (some vanilla ones are 308–396 bytes) need the tail fields
  treated as absent.
