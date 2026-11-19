# Mixing local power and reserved Bayer evidence

Recorded: 2026-11-19T02:35:23-08:00 (America/Los_Angeles).

Trained three mixtures of fixed local-power and reserved-Bayer
edge gates above the frozen local 20k phase correction. Each arm
saw 448 source photos over 672 updates. The conditional blend
adds 1.42 intact-wire response points over local power and
lowers absolute gap error by 1.70 DN16, with 2.84 DN16 more
change inside the true gaps. At similar exact-flat error, scaled
local power retains 0.10 more response points on independent
natural photos.

Viewed the three exact-target boards, two exact-flat boards
and all eight standing GFX comparisons. The sky remains smooth
and coarse crossings stay coherent. All three mixtures retain
some nominal right-side cab modulation, with incomplete fine
junctions in both profiles.
[Training, scores and triplets](../docs/phase-correction-mixture.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).

Training, scoped numerical results and native viewing are complete.
The fixed broad panels are outside this crop component study.
[Comparable PSNR history](../docs/performance-history.md).

The larger-corpus continuation verifies matched inputs through
25,000 updates on 50,000 distinct photos per arm. A live worker
started the complete 64-photo numerical evaluation and will
then evaluate both standing GFX scenes. The latest completed
matched quality review still covers 20k.
[Training audit](../docs/scene-full-epoch.md#execution-status) ·
[Full 25k review launch](../docs/results/scene-full-epoch-v1/queue-full-025000-launch.json).
