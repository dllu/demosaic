# Directional support for weak-wire breaks

Recorded: 2026-11-19T17:24:09-08:00 (America/Los_Angeles).

The 48-source holdout includes partial breaks across all wires and
staggered breaks across neighboring wires. Each view freezes the aligned
and V120 EMA outputs plus identical Bayer conditioning. Three across-wire
and five along-wire windows check the weaker direction on reciprocal
checkerboards, projecting out the continuing strong direction. Eight
RAW interventions preserve the predicted geometry and contrast scales.

At matched correction RMS, directional support lowers ISO400 false-line
projection by 0.108 DN16. At ISO6400 it loses 0.323 points of preserved weak
response and adds 0.178 DN16 false projection. Applying the exact gap mask
recovers only 0.55 more ISO6400 points at this measured lift strength.
The test leaves meaningful gains from stronger supported amplitude open.

Both standing GFX families were inspected, including both cab profiles
and JPEGs at the two display exposures. The two left crops receive small
corrections and connected crossings remain missing. The building
correction falls from 3.98 to 1.61 DN16 RGB RMS. The hard gate reproduces
the previous camera output at native display precision.

The scope is inference over frozen EMAs. No comparable fixed photo or
camera score was added to the PSNR history.

[Report and receipts](../docs/wire-segment-support.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine green mesh review map](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
