# Local Bayer phase rotation and 79,000 matched photos

Recorded: 2026-11-19T07:45:33-08:00 (America/Los_Angeles).


An inner green fit nominates a local phase for the frozen Bayer correction
while holding amplitude fixed. On 24 held-out photo backgrounds with
planted shifts, the ISO6400 response increases 2.25 points with supplied
geometry and 0.93 with noisy-only donor geometry versus the veto.
The automatic shifted-center RMS falls 1.29 DN16. Ten automatic shifted
queries change. Opposite rotation worsens the fit, and smoothly varying
carriers gain almost nothing.

I viewed both automatic exact-target comparisons, both supplied-geometry
comparisons and all eight standing boards. The coarse fence and the
transferred right cab change slightly. Fine crossings stay incomplete.
[Report and native triplets](../docs/bayer-local-phase-transfer.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

The local and spatial arms match through 39,500 updates on 79,000
distinct photos and 316,000 queries per arm. Local-only is verified
through 40k with 80,000 distinct photos. The latest completed matched
photo and camera image review is 35k, with matched 40k review queued.
Phase rotation is an inference-only experiment with the same checkpoint.
[Matched audit](../docs/results/scene-full-epoch-v1/paired-prefix-039500.json) ·
[Training and review status](../docs/scene-full-epoch.md#execution-status) ·
[Comparable PSNR history](../docs/performance-history.md).
