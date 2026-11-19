# Recover fine cab mesh with larger Bayer fits

Recorded: 2026-11-19T05:03:27-08:00 (America/Los_Angeles).

The standing high-ISO RAW and separate ISO100 exposure nominate nearly
the same two fine-cab spacings. Held-out prediction increases at the
larger fitting scale. The 64-pixel crop fit uses only the noisy exposure
after calibrating a scalar on 24 independent planted-wire backgrounds.
At ISO6400 it adds 12.26 response points and lowers intact and total
gap error by 2.56 and 2.22 DN16 versus the distant gate. It still adds
1.54 DN16 to the missing weak subspace inside true gaps. Strong-only
weak-band error changes by about −0.002 DN16. Neither ISO profile
activates the fit on the 48 natural photo backgrounds.
[Report, executable sources and exact images](../docs/bayer-carrier-scale.md).

I inspected three native exact boards, sky/building/foliage/coarse
fence and the four fine cab profile and ROI combinations. The nominal
right weave gains visible fine crossings. Some new contrast is too
regular and the weave is still incomplete. The sky, foliage and
building pixels reproduce the earlier gate. This study applies a
calibrated inference rule above frozen EMA weights and adds no broad
PSNR entries. Thirty-three focused tests passed.
[Main GFX map](../docs/gfx-qualitative.md) ·
[Cab map](../docs/gfx-green-mesh.md) ·
[PSNR coverage](../docs/performance-history.md).

The larger-corpus arms now match through 31,500 updates and 63,000
distinct photo visits with 252,000 native queries per arm. The last
complete scoped quality review covers the matched 30k EMA pair.
[Matched input audit](../docs/results/scene-full-epoch-v1/paired-prefix-031500.json) ·
[Matched 30k report](../docs/scene-full-epoch-30k.md).
