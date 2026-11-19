# Learned spectral corrections and the 17k scene prefix

Recorded: 2026-11-19T00:02:10-08:00 (America/Los_Angeles).

## Learned spectral corrections

Trained three matched pairs of achromatic heads above frozen Corpus 100k
EMA. The signed-frequency phase audit caught incorrect indexing from the
packed to the native FFT grid. Preserved those three attempts with their
original receipts, rebuilt the features and retrained all three pairs.
Corrected training, exact-target scoring and actual native review are complete.

The wider directional head gains 3.85 ISO6400 wire-response points over
Corpus 100k and 0.95 over its total-power control. It raises intact error
and adds 11.49 DN16 RMS in true gaps. The main sky stays smooth and the
fine cab mesh remains incomplete in both profiles.
[Report](../docs/learned-spectral-detail.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

The results are scoped crop measurements. The fixed full427 and
known/unseen camera panels have no corresponding new measurement in the
[PSNR history](../docs/performance-history.md).

## Large-corpus training

Published the verified 15.5k, 16k, 16.5k, 17k and 17.5k paired milestones.
The latest audits bind 35,000 distinct source photos and 140,000 native queries
per arm. The last paired exact-target and both native GFX reviews remain
the 15k EMA checkpoints.
[Coverage report](../docs/scene-full-epoch.md#execution-status) ·
[17.5k source and checkpoint audit](../docs/results/scene-full-epoch-v1/paired-prefix-017500.json).
