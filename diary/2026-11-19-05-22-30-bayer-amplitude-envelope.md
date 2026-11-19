# Package the 64-pixel Bayer fit and check local amplitudes

Recorded: 2026-11-19T05:22:30-08:00 (America/Los_Angeles).

The 64-pixel Bayer correction is available as an opt-in Python crop
function. It accesses the crop and four nearby packed RAW donor patches.
Replay reproduces 192 exact-target outputs and all eight standing
outputs bit for bit with the frozen parent. The first port replay
overwrote part of the donor bank when replacing a synthetic query. The
sealed rerun replaced only the ROI and retained the original donors.
[API and usage](../docs/usage.md#repeating-mesh-crops) ·
[Replay receipt](../docs/results/bayer-amplitude-envelope-v1/package-parity.json).

The checked green spatial envelope lowers ISO400 weak-family gap error
by 1.176 DN16 while losing 0.132 points of intact response. It changes
very little at ISO6400. Extra red and blue data raise the count of
accepted local fits without moving the gap error meaningfully. Unchecked
attenuation loses more good detail. I viewed five exact boards and all
eight standing GFX comparisons. The checked variants reproduce the
visible 64-pixel weave with residual regularity and incomplete crossings.
Fourteen focused tests pass. This inference study adds no broad scores.
[Measurement and crops](../docs/bayer-amplitude-envelope.md) ·
[Main GFX](../docs/gfx-qualitative.md) · [Cab](../docs/gfx-green-mesh.md) ·
[PSNR coverage](../docs/performance-history.md).

Both larger-corpus arms match through 32,500 updates on 65,000 distinct
photos and 260,000 native queries per arm. The fixed 64-photo and standing
GFX reviews are queued for 35k. Both use frozen source controls from the
completed 30k comparison. The final broad panels remain queued at 50k.
[Matched training audit](../docs/results/scene-full-epoch-v1/paired-prefix-032500.json) ·
[35k launch](../docs/results/scene-full-epoch-v1/queue-full-035000-launch.json).

The local-only arm reaches 33,500 verified updates on 67,000 distinct
photos, with 268,000 native queries.
[Local audit](../docs/results/scene-full-epoch-v1/local-033500-prefix.json).
