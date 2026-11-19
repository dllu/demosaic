# Fit a response-calibrated regional mixture and audit 87,000 paired photos

Recorded: 2026-11-19T09:31:39-08:00 (America/Los_Angeles).

Fit coarse and detail mixtures of frozen Corpus 100k with the matched
40k continuations. Each fit used the same 16 calibration backgrounds at
two ISO profiles with coupled and independent draws. Bounded convex
weights fall back to Corpus 100k when constrained to preserve its
fine response. The bounded opposite-direction luminance boost gives
the fit more freedom. With the spatial checkpoint, independent ISO6400
fine-flat RMS falls 0.209 DN16 and lower flat RMS falls 1.064 DN16 on
48 held-out photos. Fine response changes −0.012 points and upper-band
flat RMS rises 0.103 DN16. Quiet chroma falls 0.895 DN16. Registered
outer gate features contribute little versus local features. Replacing
spatial 40k with local-only 40k raises the flat RMS by 0.107 DN16.

Viewed two native exact triplets, the four standing main crops and
both fine cab ROIs with both noise profiles, both JPEGs and AHD.
The sky stays smooth and the fine cab crossings remain incomplete.
The output composition uses two frozen restorers. Broad continuation
panels remain queued at 50k. [Mixture report](../docs/scene-gated-mixture.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine cab](../docs/gfx-green-mesh.md) ·
[Performance history](../docs/performance-history.md).

The frozen scene continuation verifies 43,500 paired updates on 87,000
photos per arm. The local arm verifies 45,000 updates on 90,000 distinct
photos. The 40k pair remains the latest matched trained checkpoints with
complete native and photo review.
[Paired audit](../docs/results/scene-full-epoch-v1/paired-prefix-043500.json) ·
[Local audit](../docs/results/scene-full-epoch-v1/local-045000-prefix.json) ·
[40k review](../docs/scene-full-epoch-40k.md).
