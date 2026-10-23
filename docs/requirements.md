# Project goals and current evidence

**V102 is the current quality baseline in V84's architectural family.**
It reaches36.67951dB on full427,+.17604dB over V101 and about1.78dB above V43,
with higher known/unseen measured-CFA means. Fine high-noise detail remains open.
[Current choices](current-model.md) and the [README](../README.md) show useful
progress; individual study gates do not freeze those recommendations.

The broader objective in [PROMPT](../PROMPT.md) remains active. Quality has
priority over speed. The current [GFX gallery](gfx-qualitative.md) includes
complete V101/V102/V103/RawNIND frames and six native regions; learned
real-capture differences remain small.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint demosaicing and denoising | V102:36.67951dB on full427; improved measured-CFA means and cleaner geometry than RawNIND in current native comparisons | Improve fine texture, color tails and real-photo results; make strong benchmark claims only when their comparisons are complete |
| Much better real-photo quality than RawNIND | Current GFX comparisons show more coherent mesh/rails and less grain with the learned models | Broaden actual scene/camera comparisons and recover more foliage/weak detail |
| 16-bit and practical full-resolution output | Verified101.996MP RGB16 TIFFs from V101/V102/V103 and RawNIND through the shared exporter | Keep full-frame quality/precision/timing measurements specific to the selected checkpoint |
| 100MP within10s on GB10 | V102 inference/blending takes202.31s in the recorded IEEE FP32 configuration; target remains open | Optimize after improving quality |
| Modern DINOv3 method | V102 continues the official pinned ConvNeXt-Tiny pyramid and pretrained DRUNet RGB family | Continue quality improvements and assess other approaches when useful |
| Free, diverse targets and aggressive binning | V104 trains on90,872 reviewed sources; next90,864 removes eight further source-specific targets;4×→geometry→area2 | Measure the larger corpus and the cleaned Tiny/Small trial; retain source/detail review |
| Physical noise/exposure and camera handling | Poisson/read noise, negative black-subtracted values, Bayer phases, clipping and WB/matrix conditioning are implemented | Continue testing shadows, saturated lights, color and low-noise behavior |
| Reliable training and resource use | Source/manifest snapshots, restart checks, bounded jobs and actual CPU/CUDA operation | Monitor current runs and retain failures/results accurately |
| Protected originals and evaluation scenes | Originals read-only; cached GFX3879/3880 and siblings excluded from training | Preserve those boundaries in new data recipes |
| Current documentation and reproducibility | Native crops with source/ROI/weights/noise/display metadata; local-time diary; Git history | Update README/current guides and comparisons when good versions appear |

## Active quality work

[V102 final20k is the current quality baseline](v102-v103-quality-review.md),
continuing V84's DRUNet/frozen DINOv3 ConvNeXt-Tiny family with zero optical PSFs,
weak textures,photographic contrast attenuation and six reviewed ROIs. It gains
+.17604dB over V101 on full427,with425 source means improving and higher
known/unseen CFA means. V103 has nearly identical photo quality; V102's flat-color
and weak-carrier diagnostics favor it overall. All seven evaluation panels and
complete102MP GFX exports finished and were independently checked. Fine
high-noise texture,foliage and saturated-light detail remain weaknesses.

V104's reviewed **90,872-source** corpus adds2,395 eligible arrivals. Native
source views,duplicate/content/title/series exclusions,protected holdouts and
actual reader checks are documented in the [incoming review](incoming-commons-quality.md).
V104 is training from V102 on this cohort; its trained benefit remains unmeasured. Earlier570-source/31-exclusion review and six/32-ROI studies
retain their frozen inputs and receipts. [Training/data details](quality-first-training.md).

The completed incoming source screen and native follow-up freeze a separate
**90,864-source** future cohort: three visibly degraded photo targets and five
atlas reproductions are additionally withheld. The V109 Tiny/V110 Small
recipes pass actual discarded CPU and CUDA checks, but their production runs
remain unlaunched pending V104 review. [Current capacity preparation](convnext-small-capacity.md#prepared-matched-quality-trial).

[Current native detail](heldout-detail.md),[camera](real-camera-quality.md) and
[GFX full-frame](gfx-qualitative.md) galleries show useful gains and remaining
weaknesses. The merged [linear DNG/JPEG path](dng-export.md) adds optional Bayer
hot-pixel removal before restoration. Its default-off repair does not alter
these completed comparisons. The [16-scene paired test reserve](paired-reserved-test.md)
remains prepared,unscored and outside model selection.

The [experiment index](experiments.md) and [PSNR history](performance-history.md)
retain earlier gains and tradeoffs. For example, V95 improves a tested weak
carrier, while V98/V99 improve ADC color but retain positive-noise color/detail
issues. These observations inform the current recipe without making V43 the
default again.

## Evidence for the full objective

Assess useful trained versions against the current baseline and strong
comparators on the fixed photographic/camera panels and actual native images.
Retain source/scene intervals and adverse cases. Each reported improved model
needs at least two native noisy/restored/GT crop triplets with matching
coordinates/transforms, checkpoint hash, conditioning and display exposure.
Real AHD/separate ISO100 references remain nonexact and are not pixelwise GT.

Show credible improvements and update current examples as they appear. Claims
such as state-of-the-art quality, broad real-camera superiority or a particular
100MP runtime need evidence covering those claims; they are not prerequisites
for documenting an improved implementation or choosing a better baseline.

The [diary](../diary/index.md) and [historical evidence log](requirements-archive.md)
retain prior decisions. Existing machine receipts preserve original bytes and
study-specific decisions, while current prose reflects today's implementation.
