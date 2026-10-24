# Project goals and current evidence

**V112 final20k is the current restoration and quality-training baseline.**
It reaches36.90238dB on all427 photos, +.10154dB over V104, with425 source means
improving. Known/unseen CFA means are54.26914/53.95378dB; worst ADC flat bias
falls to50.89DN16. [Current choices](current-model.md) · [Complete review](v112-quality.md).

The full [PROMPT](../PROMPT.md) objective remains active. Fine real foliage,
weak detail and adverse-camera behavior still need work. The stronger released
RawNIND remains competitive on real-camera scenes; source means and the small
GFX gallery do not establish broad real-camera superiority. Quality precedes speed.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint restoration | V112 full-photo36.90238dB,425/427 source gains and improved8/16-pixel weak carriers | Recover finer detail and reduce adverse cases before SOTA claims |
| Much better real-photo quality than RawNIND | Complete V112/V104/half/pre-upsampled GFX frames and six native regions; learned models retain more regular mesh | Improve fine foliage and broaden real-camera evidence |
| 16-bit/full-resolution output | Complete101.996MP V112 linear/sRGB RGB16 exports rehashed/reopened; original exporter compared33 decoded full-width rows per file with floats | Preserve per-checkpoint quality/precision evidence |
| 100MP within10s on GB10 | V112 FP32 inference/blending167.51s, tile512/overlap64/B4 | Target open; improve quality before speed work |
| Modern DINOv3 architecture | V84-family DRUNet RGB trunk and official frozen ConvNeXt-Tiny pyramid | Transfer the larger frozen Small encoder from the stronger V112 parent |
| Diverse clean targets and binning |90,864-source cleaned corpus;4×→geometry→area2, zero optical blur, weak textures/photo contrast, six reviewed ROIs | Retain visual source review and fine-detail coverage |
| Physical noise/camera/color | Poisson/read noise, signed black subtraction, all Bayer phases, WB/matrix, exposure/clipping; V112 repairs large ADC tails | Spatial dark-field/weak-detail failures remain |
| Reliable resource-aware training | Exact parent/source/data snapshots, actual checks, fixed endpoints and retained failures; V112-derived Tiny/Small passed CPU updates | Queued matched continuations after the original GPU chain, then endpoint quality review |
| Protected originals/tests | Local GFX3879/3880 cache; originals read-only; standing scene/siblings outside training;16-scene test reserve unscored | Preserve boundaries in future cohorts |
| Current documentation |46 completed primary endpoints in plot; native triplets with source/ROI/hash/noise/display; local-time diary | Update as useful results complete, without old promotion freezes |

## Current work and evidence

[All seven V111/V112 panels](v112-quality.md) are complete. V112 has V111-like
photo PSNR and better camera/color results; independent Torch64 arithmetic
checks all4704 saved color predictions. Actual native review covers material,
ADC failures, all six GFX contexts and complete full-frame comparisons.
[Primary statistics](v111-v112-primary-quality.md) ·
[Full-frame receipt](results/v112-fullframe-review-v1.json).

The original V104 [eight-view full 102MP export and native review](dihedral-fullframe.md)
are complete; its broad evaluation/audit remains in progress. The V112-derived
Small initializer and actual CPU updates are verified. [Matched Tiny/Small
continuations](small-aligned-training.md) are queued for 20,000 further updates
each after the original GPU chain. Source/scene intervals describe fixed
evaluation units and do not measure training-repeat uncertainty.

Each improved-model report needs at least two native noisy/restored/exact-GT
triplets with common coordinates/transforms and recorded weights, conditioning
and display exposure. Real AHD/separate ISO100 references stay explicitly
nonexact. [Current GFX gallery](gfx-qualitative.md) · [Version history](performance-history.md).
Hot-pixel repair and [linear DNG/JPEG output](dng-export.md) are merged; repair
was off in these comparisons.

Useful prior results and original receipts remain intact:
[V104](v104-reviewed-corpus-quality.md), [V102/V103](v102-v103-quality-review.md),
[V111 material/analytic results](v111-early-quality.md) and the
[stronger RawNIND comparison](rawnind-variants.md). Current implementation choices
follow useful quality gains, not old study-specific significance gates.
