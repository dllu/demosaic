# Matched low-noise endpoints completed

Recorded: 2026-11-18T03:21:27-08:00 (America/Los_Angeles).

The near-ADC continuation and its equal-budget control both completed
800 updates and 12,800 target slots from the same immutable 100k EMA.
The control took 637.34 seconds and the new arm 642.80 seconds, including
worker-loop validation and saves. The exact source/crop traces and camera
metadata match. The new arm resimulates 483 of the 980 original ADC-only
slots across Commons and native simulation. Measured paired slots match.
[Training report](../docs/near-adc-bridge-training.md) ·
[Checkpoint and recovery evidence](../docs/results/near-adc-bridge-training-v1/completed-training.json).

A stale receipt path stopped the first post-training audit. Both
completed checkpoints passed verification after the path was corrected.
The native and faint-photo evaluations are now collecting against the 100k
parent, matched control and saved V120 where available. The scorer
replayed 640 prior numerical rows exactly. Actual native inspection
and broad benchmark scores remain pending. The 100k parent has the
latest completed retained native review.
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
