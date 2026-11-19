# Adaptive Bayer blending and 58,000 matched training photos

Recorded: 2026-11-19T04:12:19-08:00 (America/Los_Angeles).


The adaptive near/wide blend learns mostly about the strength of the
parallel change. This component accounts for 0.622 of its 0.626-point
ISO6400 wire response gain over the nearest operator. A constant 76.52%
wide blend matched on calibration gaps gives effectively the same held-out
wire response and absolute gap error. The adaptive arm gains 0.061 natural
response points against the stronger flat-matched constant control and
costs about twice the eight-donor CPU correction time. Exact targets and
both standing GFX families were viewed. Fine cab crossings stay incomplete.
[Experiment and frozen state](../docs/bayer-phase-shrinkage.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine cab mesh](../docs/gfx-green-mesh.md).

The continued scene training has verified identical inputs through 29,000
updates and 58,000 photos for each arm. Local-only reached 30,000 with
60,000 photos. The 30k review remains queued for the matched pair.
[Coverage and review queue](../docs/scene-full-epoch.md#execution-status) ·
[Last complete quality review](../docs/scene-full-epoch-25k.md) ·
[Comparable PSNR history](../docs/performance-history.md).
