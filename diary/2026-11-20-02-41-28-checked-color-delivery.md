# Check neutral Bayer delivery against held color samples

Recorded: 2026-11-20T02:41:28-08:00 (America/Los_Angeles).

Split each red and blue lattice into complementary checkerboards.
Fit signed amplitude in a 48-pixel window with the pooled green
phase, verify the broad window and 32-pixel center, and hold the
delivered green fixed. Conditional delivery replaces the neutral
color only when both held folds contradict its red or blue prediction.

On the prior exact reversal, conditional RGB RMS drops from 136.31
to 93.40 DN16 at original variance and from 125.55 to 102.57 with
double variance. Original-variance aligned RGB error remains 55.72
DN16. Across new signed camera draws from 24 photo backgrounds the
local RGB gain is 0.471 DN16 relative to neutral. The effect is
suppression in all 48 contradicted windows. None clears the signed
amplitude check, and the local weak-increment RMS still trails
both parent observations.

Viewed both standing GFX families and the exact triplets. The main
scene reproduces pooled-color. One transferred left-cab red window
changes, and fine crossings remain incomplete. The unconditional
method looks greener where weak R/B samples lack support.

[Report](../docs/cfa-signed-color-delivery.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).
