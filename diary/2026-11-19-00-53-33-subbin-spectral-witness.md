# Refining between-bin Bayer phase

Recorded: 2026-11-19T00:53:33-08:00 (America/Los_Angeles).

## Continuous frequency transport

Used disjoint nearby green samples to refine the frequency between FFT
bins before measuring signed support on the center Bayer sites. The
known-direction audit found stronger phase agreement and gap separation.
Trained three matched heads on the existing 448 photos. The transported
proposal improves held-out ISO6400 intact response by 0.50 points and
absolute gap RMS by 1.30 DN16 at similar added gap texture. It retains
higher intact error than Corpus 100k and gives no convincing new
real cab crossings. A separate gate on the stronger analytic lift
loses true signal at comparable gap change.

All eight standing boards, two exact comparison boards and six native
triplets were reviewed. The initial review import failure is preserved.
Training, scoped numerical evaluation and native review are complete.
The component supplies no new full-photo or known/unseen camera point
for the comparable [PSNR history](../docs/performance-history.md).
[Report](../docs/subbin-spectral-witness.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

## Matched larger-corpus checkpoint

Published paired audits from 18.5k through 20k. At 20k, both arms verify
40,000 distinct photos and 160,000 native queries with identical source
traces. The 20k review worker starts with the 64-photo exact-target
collection and follows with both standing scenes. The latest complete
matched quality review remains 15k.
[Execution status](../docs/scene-full-epoch.md#execution-status) ·
[Paired 20k audit](../docs/results/scene-full-epoch-v1/paired-prefix-020000.json) ·
[Review queue](../docs/results/scene-full-epoch-v1/queue-review-020000-launch.json).
