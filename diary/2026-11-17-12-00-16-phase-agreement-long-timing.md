# Phase agreement and retained long-training timing

Recorded: 2026-11-17T12:00:16-08:00 (America/Los_Angeles).

The matched phase-agreement experiment shares the pooled gate and weights
the delivered correction by the positive cosine between the two fitted
phase profiles. All 392 pooled threshold-2 predictions match their retained
counterparts exactly. On the seven correctly guided ISO6400 far geometries,
weak-fit agreement is positive in 53.6% of color-specific fits whether the
weak wire is present or absent. The two missed weak guides remain included
in reconstruction metrics. At the tightest quiet budget, ISO400 far weak
response falls from 16.89% to 15.60%, with quiet cost 0.02306 to 0.02281 DN16
and high-noise gain unresolved. The measured building correction falls
from 0.421 to 0.166 DN16 RMS, and the sky matches V120. Both cab ROIs still
lack convincing fine crossings. All ten boards were opened, and the
independent audit reproduces 1,152 direct-pixel reductions.
[Results and native crops](../docs/phase-profile-agreement.md) ·
[Main GFX map](../docs/gfx-qualitative.md) · [Cab mesh map](../docs/gfx-green-mesh.md).

The 100k run reached update 22,000. The two logged training loops through
20k total 13,127.97 seconds. This tally excludes the pause between phases
and the final checkpoint write. The matched three-model CPU review is
processing the remaining inputs and its independent audit waits for the
original collector to finish. Last completed checkpoint-quality comparison
is the separate control20k. The existing broad panel scores remain the
last comparable PSNR-history points.
[Scaling and timing](../docs/full-corpus-scaling.md#long-schedule-20k-milestone) ·
[Comparable PSNR coverage](../docs/performance-history.md).
