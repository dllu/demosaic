# Project goals and current evidence

**V114 Tiny is the general restoration and quality-training baseline.**
It reaches36.97973dB on all427 photos, +.07735 over V112, with422 source means
improving. Known/unseen measured-CFA means are54.28627/54.00290dB.
Small improves the known-camera mean and eight-pixel carrier response, while
Tiny has slightly higher photo PSNR and lower color bias.
[Current choices](current-model.md) · [Complete comparison](v114-v115-quality.md).

The full [PROMPT](../PROMPT.md) objective remains active. Real foliage, finest
weak detail and dark-camera behavior still need work. The stronger released
RawNIND wins four of nine camera scene means; this small development set and
the GFX gallery do not establish broad real-camera superiority. Quality precedes speed.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint restoration | V114 photo36.97973dB,422/427 source gains over V112; improved8/16px carrier response | Recover finest detail and reduce adverse cases before SOTA claims |
| Much better real-photo quality than RawNIND | Complete Tiny/Small GFX frames, six native regions and nine measured-camera scene comparisons; coherent mesh | Reduce foliage/neon smoothing and dark-field mottling; broaden real-camera evidence |
| 16-bit/full-resolution output | Both101.996MP linear/sRGB RGB16 exports rehashed/reopened;921,600 native channel values match original quantization | Preserve per-checkpoint precision/quality evidence |
| 100MP within10s on GB10 | Ordered Tiny/Small FP32 observations116.57/101.66s, not a controlled speed ranking | Target open; improve quality before speed work |
| Modern DINOv3 architecture | V84-family DRUNet and official frozen Tiny/Small pyramids; completed matched trained comparison | Retain useful gains and improve finer detail |
| Diverse clean targets and binning |90,864 reviewed sources;4×→geometry→area2, zero optical blur, six ROIs, weak textures/photo contrast | V116 fine-source/reference-mask quality remains unmeasured |
| Physical noise/camera/color | Poisson/read noise, signed black subtraction, all Bayer phases, WB/matrix and exposure/clipping; Tiny ADC/high-noise max bias51.73/85.40DN16 | Spatial dark-field/weak-detail failures remain |
| Resource-aware training and evaluation | Exact source/parent snapshots and retained failures; completed Tiny/Small panels plus V116's20k training audit | Finish V116's running full evaluation and inspect its complete saved-output review |
| Protected originals/tests | Local GFX3879/3880 cache; originals read-only; standing scene/siblings outside training;16-scene test reserve unscored | Preserve boundaries in future cohorts |
| Current documentation |48 completed primary endpoints in plot; native triplets and GFX comparisons with metadata; local-time diary | Update useful results without promotion freezes |

The [V116 data trial](fine-detail-data-training.md) passed its eight discarded
CUDA updates and completed its original20k run. Its matched Tiny control is V114;
the original V112 initializer/seed/budget stay fixed. A single-candidate evaluator
is running; independent audit and direct saved-output comparison are waiting downstream.
Trained quality and actual native review remain pending. A separate
[V114 eight-view pilot](v114-eight-view.md) is complete on24 saved observations,
improving selected material/camera scores with a color-bias tradeoff. Its full
panels/frame remain unmeasured; it does not close broad real-quality or speed goals.

Hot-pixel repair and [linear DNG/JPEG output](dng-export.md) are merged; repair
was off in these comparisons. Each improved-model report includes at least two
native noisy/restored/exact synthetic GT triplets. Separate ISO100/AHD RGB
references remain explicitly nonexact. [GFX gallery](gfx-qualitative.md) ·
[Version plot](performance-history.md) · [Historical evidence](requirements-archive.md).
