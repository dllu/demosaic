# Discovery-fold shrinkage and the long-schedule 20k checkpoint

Recorded: 2026-11-17T11:22:54-08:00 (America/Los_Angeles).

The long schedule saved update 20,000. The audit compared the actual
20,000 source/crop/seed rows, 80 conditioning chunks, and saved Python,
CPU and CUDA RNG states against the completed short schedule. The declared
order-header hashes account for the difference in the source rows.
The long checkpoint contains a complete finite model, EMA and Adam state.
Both schedules had visited all 90,778 ordinary training photos by update
17,039. The separately annealed control and the long milestone now enter
a fresh matched comparison with V120 on 110 retained inputs.
[Training and launch evidence](../docs/full-corpus-scaling.md#long-schedule-20k-milestone).

The detail experiment tests whether subtracting expected fitted noise energy
on each discovery fold reduces false texture from the richer phase fit.
It reuses the previous phase study's draw, guides, crops and thresholds.
The original files, outputs and receipts remain available by hash.

At ISO6400 far and threshold 0, shrinkage reduces quiet error from 8.349 to
7.640 DN16 and weak-increment error from 22.761 to 22.570 DN16.
The weak response also falls from 11.58% to 5.96%. Both error costs improve
on every geometry at this gate and remain above the parent means. The
threshold-2 ISO400 far result is nearly unchanged. All 14 native boards
were opened, with both GFX families still showing incomplete fine detail.
[Detail report](../docs/guided-phase-fit-shrinkage.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Cab mesh review map](../docs/gfx-green-mesh.md).

The long-schedule image review, full photo panels and faint ADC study are
still collecting. The completed synthetic and GFX evidence is scoped here.
[Comparable PSNR panel coverage](../docs/performance-history.md).
