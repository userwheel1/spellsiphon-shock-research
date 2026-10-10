"""EFSH DATA layout for Skyrim SE, in xDump/xEdit field order.

Derived by correlating the xDump 4.1.5f decoded output of
  * Spellsiphon.esp  EFSH 0403603E <KSSC_ShockShader>
  * Skyrim.esm       EFSH 0010BEAC <AlchArmorShockFXS>
with the raw 400-byte DATA payload of each record, and verified by
tools/validate_layout.py (every field is cross-checked against xDump).

Each entry is (byte_offset, kind, name) where kind is:
  'u32'   - raw 32-bit value (blend modes, packed colour, counts)
  'f32'   - float
  'rgb'   - colour packed in a u32; red is the LOW byte (0x00BBGGRR)
"""

DATA_LEN = 400

LAYOUT = [
    # Membrane shader specular colour (4 packed channels, red is the LOW byte)
    (0,   'rgb', 'Membrane Shader - Specular Color'),
    (4,   'u32', 'Membrane Shader - Specular Strength'),
    (8,   'u32', 'Membrane Shader - Specular Color Scale'),
    (12,  'u32', 'Membrane Shader - Unknown12'),

    (16,  'rgb', 'Fill/Texture Effect - Color Key 1'),
    (20,  'f32', 'Fill/Texture Effect - Alpha Fade In Time'),
    (24,  'f32', 'Fill/Texture Effect - Full Alpha Time'),
    (28,  'f32', 'Fill/Texture Effect - Alpha Fade Out Time'),
    (32,  'f32', 'Fill/Texture Effect - Presistent Alpha Ratio'),
    (36,  'f32', 'Fill/Texture Effect - Alpha Pulse Amplitude'),
    (40,  'f32', 'Fill/Texture Effect - Alpha Pulse Frequency'),
    (44,  'f32', 'Fill/Texture Effect - Texture Animation Speed (U)'),
    (48,  'f32', 'Fill/Texture Effect - Texture Animation Speed (V)'),

    (52,  'f32', 'Edge Effect - Fall Off'),
    (56,  'rgb', 'Edge Effect - Color'),
    (60,  'f32', 'Edge Effect - Alpha Fade In Time'),
    (64,  'f32', 'Edge Effect - Full Alpha Time'),
    (68,  'f32', 'Edge Effect - Alpha Fade Out Time'),
    (72,  'f32', 'Edge Effect - Persistent Alpha Ratio'),
    (76,  'f32', 'Edge Effect - Alpha Pulse Amplitude'),
    (80,  'f32', 'Edge Effect - Alpha Pulse Frequency'),

    (84,  'f32', 'Fill/Texture Effect - Full Alpha Ratio'),
    (88,  'f32', 'Edge Effect - Full Alpha Ratio'),
    (92,  'u32', 'Membrane Shader - Dest Blend Mode'),

    (96,  'u32', 'Particle Shader - Source Blend Mode'),
    (100, 'u32', 'Particle Shader - Blend Operation'),
    (104, 'u32', 'Particle Shader - Z Test Function'),
    (108, 'u32', 'Particle Shader - Dest Blend Mode'),

    (112, 'f32', 'Particle Shader - Particle Birth Ramp Up Time'),
    (116, 'f32', 'Particle Shader - Full Particle Birth Time'),
    (120, 'f32', 'Particle Shader - Particle Birth Ramp Down Time'),
    (124, 'f32', 'Particle Shader - Full Particle Birth Ratio'),
    (128, 'f32', 'Particle Shader - Persistant Particle Count'),
    (132, 'f32', 'Particle Shader - Particle Lifetime'),
    (136, 'f32', 'Particle Shader - Particle Lifetime +/-'),
    (140, 'f32', 'Particle Shader - Initial Speed Along Normal'),
    (144, 'f32', 'Particle Shader - Acceleration Along Normal'),
    (148, 'f32', 'Particle Shader - Initial Velocity #1'),
    (152, 'f32', 'Particle Shader - Initial Velocity #2'),
    (156, 'f32', 'Particle Shader - Initial Velocity #3'),
    (160, 'f32', 'Particle Shader - Acceleration #1'),
    (164, 'f32', 'Particle Shader - Acceleration #2'),
    (168, 'f32', 'Particle Shader - Acceleration #3'),
    (172, 'f32', 'Particle Shader - Scale Key 1'),
    (176, 'f32', 'Particle Shader - Scale Key 2'),
    (180, 'f32', 'Particle Shader - Scale Key 1 Time'),
    (184, 'f32', 'Particle Shader - Scale Key 2 Time'),

    (188, 'rgb', 'Color Key 1 - Color'),
    (192, 'rgb', 'Color Key 2 - Color'),
    (196, 'rgb', 'Color Key 3 - Color'),
    (200, 'f32', 'Color Key 1 - Color Alpha'),
    (204, 'f32', 'Color Key 2 - Color Alpha'),
    (208, 'f32', 'Color Key 3 - Color Alpha'),
    (212, 'f32', 'Color Key 1 - Color Key Time'),
    (216, 'f32', 'Color Key 2 - Color Key Time'),
    (220, 'f32', 'Color Key 3 - Color Key Time'),

    (224, 'f32', 'Particle Shader - Initial Speed Along Normal +/-'),
    (228, 'f32', 'Particle Shader - Initial Rotation (deg)'),
    (232, 'f32', 'Particle Shader - Initial Rotation (deg) +/-'),
    (236, 'f32', 'Particle Shader - Rotation Speed (deg/sec)'),
    (240, 'f32', 'Particle Shader - Rotation Speed (deg/sec) +/-'),

    (244, 'u32', 'Addon Models'),
    (248, 'f32', 'Holes - Start Time'),
    (252, 'f32', 'Holes - End Time'),
    (256, 'f32', 'Holes - Start Val'),
    (260, 'f32', 'Holes - End Val'),
    (264, 'f32', 'Edge Width (alpha units)'),
    (268, 'rgb', 'Edge Color'),
    (272, 'f32', 'Explosion Wind Speed'),
    (276, 'u32', 'Texture Count U'),
    (280, 'u32', 'Texture Count V'),
    (284, 'f32', 'Addon Models - Fade In Time'),
    (288, 'f32', 'Addon Models - Fade Out Time'),
    (292, 'f32', 'Addon Models - Scale Start'),
    (296, 'f32', 'Addon Models - Scale End'),
    (300, 'f32', 'Addon Models - Scale In Time'),
    (304, 'f32', 'Addon Models - Scale Out Time'),
    (308, 'u32', 'Ambient Sound'),

    (312, 'rgb', 'Fill/Texture Effect - Color Key 2'),
    (316, 'rgb', 'Fill/Texture Effect - Color Key 3'),

    # Fill/Texture Effect - Color Key Scale/Time
    (320, 'f32', 'Fill Color Key 1 - Scale'),
    (324, 'f32', 'Fill Color Key 2 - Scale'),
    (328, 'f32', 'Fill Color Key 3 - Scale'),
    (332, 'f32', 'Fill Color Key 1 - Time'),
    (336, 'f32', 'Fill Color Key 2 - Time'),
    (340, 'f32', 'Fill Color Key 3 - Time'),

    (344, 'f32', 'Color Scale'),
    (348, 'f32', 'Birth Position Offset'),
    (352, 'f32', 'Birth Position Offset Range +/-'),

    # Particle Shader Animated
    (356, 'u32', 'Start Frame'),
    (360, 'u32', 'Start Frame Variation'),
    (364, 'u32', 'End Frame'),
    (368, 'u32', 'Loop Start Frame'),
    (372, 'u32', 'Loop Start Variation'),
    (376, 'u32', 'Frame Count'),
    (380, 'u32', 'Frame Count Variation'),

    (384, 'u32', 'Flags'),
    (388, 'f32', 'Fill/Texture Effect - Texture Scale (U)'),
    (392, 'f32', 'Fill/Texture Effect - Texture Scale (V)'),
    (396, 'f32', 'Scene Graph Emit Depth Limit (unused)'),
]

BY_NAME = {}
for _off, _kind, _name in LAYOUT:
    BY_NAME[_name] = (_off, _kind)

assert len(LAYOUT) == DATA_LEN // 4, f'expected 100 fields, got {len(LAYOUT)}'
assert LAYOUT[-1][0] + 4 == DATA_LEN, 'layout must exactly cover the 400-byte DATA payload'
