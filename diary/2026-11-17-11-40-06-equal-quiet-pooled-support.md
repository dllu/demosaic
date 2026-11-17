# Matching quiet error and testing pooled RAW support

Recorded: 2026-11-17T11:40:06-08:00 (America/Los_Angeles).

The equal-quiet check compares discovery-only phase shrinkage with one
uniform scale on the original correction at ISO6400 and threshold 0.
The scale is chosen per geometry using the exact quiet targets across all
four CFAs. All 16 geometry and placement pairs match. Far from the edge,
shrinkage lowers mean absolute absent projection from 1.278% to 1.024%
and weak-increment RMS from 22.621 to 22.596 DN16. Mean weak response
falls from 8.424% to 5.958%. Near the edge, strong response increases,
while weak-increment error rises in seven geometries. A direct audit of
the actual restored pixels reproduces all 192 reductions.
[Matched comparison](../docs/guided-phase-fit-shrinkage.md#iso6400-at-equal-measured-quiet-error).

The next experiment shares every discovery fit between the minimum and
pooled support gates. Both retain the veto from either fold. It uses an
eight-threshold sweep and chooses settings on the seven geometry controls
for each held-out geometry. The four-group preflight reproduces 36 old
controls and verifies 12 direct quiet RMS computations. All 384 synthetic
views and eight camera cases then complete. At the tightest calibration
budget, pooling improves ISO400 far weak response on all eight held-out
geometries, from 14.19% to 16.89% on average. Mean excess quiet RMS changes
from 0.02370 to 0.02306 DN16, and weak-increment RMS falls by 0.01693 DN16.
The ISO6400 far gain is smaller and carries higher increment error.
All ten native boards were opened. The sky stays identical to V120 and
fine cab crossings remain unresolved.
[Pooled support results](../docs/fold-support-pooling.md) ·
[Main GFX map](../docs/gfx-qualitative.md) · [Cab mesh map](../docs/gfx-green-mesh.md).

The ongoing long-schedule 20k review reproduces 54 V120/short-schedule
control arrays in its first 27 cases. The new long-schedule predictions
are distinct throughout that prefix. Quality scores require the pending
full reviews. [Training progress](../docs/full-corpus-scaling.md#long-schedule-20k-milestone) ·
[Reviewed PSNR coverage](../docs/performance-history.md).
