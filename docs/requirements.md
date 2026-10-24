# Project goals and current evidence

**V104 is the working quality baseline for positive-noise RAW and continued
training in V84's architectural family.** It reaches 36.80085dB on full427,
+.12134dB over V102 and about1.90dB over V43, with stronger known-camera and
weak-texture results. V102 retains lower ADC flat-color bias and a higher
unseen-camera mean. [Current choices](current-model.md) and the [README](../README.md)
show gains and remaining weaknesses directly.

The broader objective in [PROMPT](../PROMPT.md) remains active. Quality has
priority over speed. The [GFX gallery](gfx-qualitative.md) now compares complete
V102/V104/RawNIND frames and six native regions. Real model differences remain
small, and fine foliage and saturated-light detail still need work.

The stronger [released RawNIND pre-upsampled reference](rawnind-variants.md)
improves eight of nine development scene means over the earlier reference and
nearly matches V104 on known-camera CFA PSNR. Current synthetic-detail gains
therefore remain separate from the unachieved broad real-camera objective.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint demosaicing and denoising | V104 reaches36.80085dB on full427, improves424/427 source means and has stronger tested weak carriers | Improve fine texture, ADC color tails and real-photo results; complete broad comparisons before making SOTA claims |
| Much better real-photo quality than RawNIND | Current native GFX comparisons show clearer mesh/rails with learned models | Broaden scene/camera comparisons and recover more foliage/weak detail |
| 16-bit and practical full-resolution output | Six current101.996MP linear/sRGB RGB16 TIFFs rehashed/reopened; earlier exports preserved | Keep quality/precision/timing evidence specific to each selected checkpoint |
| 100MP within10s on GB10 | V104 inference/blending takes168.73s in the current IEEE FP32 run; target remains open | Optimize after improving quality |
| Modern DINOv3 method | V104 uses the official pinned ConvNeXt-Tiny pyramid and pretrained DRUNet RGB family | Continue quality improvements and assess useful alternatives |
| Free, diverse targets and aggressive binning | V104 completed20k on90,872 sources; active90,864-source trial removes eight further targets;4×→geometry→area2 | Measure the matched loss-scale trial and later capacity comparison; retain visual source/detail review |
| Physical noise/exposure and camera handling | Poisson/read noise, negative black-subtracted values, Bayer phases, clipping and WB/matrix conditioning implemented | Improve low-noise color and test shadows/saturated lights across cameras |
| Reliable training and resource use | Source/manifest snapshots, exact resume checks and actual CPU/CUDA operation; queue failures retained and corrected | Monitor the active fixed budgets and preserve evidence |
| Protected originals and evaluation scenes | Originals read-only; cached GFX3879/3880 and siblings excluded from training | Preserve these boundaries in future cohorts |
| Current documentation and reproducibility | Current native triplets with source/ROI/weights/noise/display metadata, updated plot, local-time diary and Git history | Refresh comparisons as useful models complete |

## Active quality work

[V104's completed review](v104-reviewed-corpus-quality.md) covers all seven
panels, the selected material test and complete 102MP exports. Photographic,
known-camera and weak-carrier results improve over V102, while the unseen-camera
mean falls and the ADC flat-color maximum rises. These tradeoffs remain visible
alongside the gains. More training, seed and corpus change together, so the
result does not isolate the data-cleaning effect.

The [V111/V112 loss-scale trial](loss-scale-training.md) retains the exact V104
EMA and learned fusion gates on the further-cleaned **90,864-source** corpus.
V111 is training; V112 follows at its fixed20k budget, changing only epsilon
.001→.0003. Actual CPU/CUDA checks and the corrected production handoff are
recorded. The earlier Tiny/Small capacity recipes remain unlaunched and can use
a better completed initializer later. [Source review](incoming-commons-quality.md) ·
[Current training](quality-first-training.md).

The [V104 ADC diagnostics](v104-adc-color-projection.md) show that the existing
Malvar residual operator repairs most flat-color bias, with texture gains and
individual phase regressions. The [completed full427/four-CFA study](adc-consistency.md)
supports an optional V104 sites export: +.28850dB, all 1,708 cases improving,
with actual serialized-export parity checks. Flat-color limitations remain;
the original positive-noise/training checkpoint is unchanged. New
[unseen-camera adverse views](real-camera-quality.md#targeted-dark-field-regressions)
retain spatial-residual weaknesses alongside the gains.

The merged [linear DNG/JPEG path](dng-export.md) adds optional Bayer hot-pixel
removal before restoration; repair was off in these comparisons. The
[16-scene paired test reserve](paired-reserved-test.md) remains unscored and
outside selection. The [experiment index](experiments.md) and
[PSNR history](performance-history.md) preserve earlier gains and tradeoffs.

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
