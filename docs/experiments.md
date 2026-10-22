# Experiment index

**V101 is the current development checkpoint in V84's architectural family.**
Its 36.50347 dB photographic result is +.06351 dB over V84 and about 1.60 dB above V43,
with close measured-CFA means and remaining high-noise texture loss. V95 remains
a useful weak-detail comparison. Study-specific statistical gates do not freeze
the baseline or prevent publishing useful gains and tradeoffs.

[Current model choices and images](current-model.md) ·
[Current quality training](quality-first-training.md) ·
[PSNR history and full table](performance-history.md) ·
[GFX comparisons](gfx-qualitative.md) ·
[Experiment archive](experiment-archive.md).

![PSNR history](images/version-PSNR-history.png)

The figure describes completed checkpoints with different architectures,
initializers, data and training horizons. It shows real progress; use the linked
matched studies when attributing a gain to a particular change.

## What the main experiment families established

| Family | Main finding | Evidence |
| --- | --- | --- |
| Geometry and original V43 | Geometry/PSF before the final 2× reduction helped the matched photo test. Diverse native targets and the full-resolution RGB/DINOv3 ViT-S model established the earlier ViT-S baseline | [V34/V36](geometry-corpus-v34-v36-review.md), [V43 step 2000](native-corpus-2k-review.md) |
| Larger Commons corpus and longer training | Established the stronger ConvNeXt-pyramid family; the isolated corpus expansion adds a modest photographic gain | [V63/V64 original20k](long-commons-v63-v64-original20k-review.md) |
| Color coordinates and supervision | Normalization, objective and camera-supervision changes produced tradeoffs | [V68/V69](normalization-v68-v69-original4k-review.md), [V74/V75](reconstruction-objective-first1k-review.md), [V76/V77](camera-supervision-first1k-review.md) |
| Compact RAW-native architecture | The completed mixed-batch experiment remains far below the mature RGB models on primary panels | [V72/V73](packed-isotropic-mixed16-quarter-review.md) |
| Directional, interval and bank heads | Several heads improve photographic means, with camera/detail tradeoffs; the simpler V84 family is stronger overall in the completed primary scores | [V78/V79](directional-interval-original4k-review.md), [V80/V81](directional-bank-original4k-review.md), [V82/V83](bank-detachment-original4k-review.md) |
| Native data and larger context | V84/V85 reach36.44dB and provide the current quality baseline. The extra native captures have little matched effect; larger context is a separate small-effect comparison | [V84/V85](native-data-original20k-review.md), [V86/V87](training-context-original4k-review.md) |
| Spectral and late RGB refinement | Small matched mean gains or protected common weights did not fix weak detail; head-only V92 regressed | [V88/V89](spectral-original4k-review.md), [V90/V91](late-rgb-original4k-review.md), [V92](late-rgb-head-only-original4k-review.md) |
| ADC-only inference | With unchanged V84 weights, replacing only valid measured sites gains .400dB rendered PSNR across all427 sources/all1,708 CFA cases. SSIM/detail/chroma have documented individual tradeoffs; positive-noise profiles bypass it | [Complete site-consistency comparison and native crops](adc-consistency.md) |

Each complete quality review retains source/checkpoint identities, native
noisy/restored/reference crops and explicit real-reference limitations. The
[chronological archive](experiment-archive.md) preserves the longer record,
including early versions, negative studies and engineering details.

## Data and current quality work

V100/V101 completed10k continuations from V84 on the curated88,484-source Commons cohort. One
retains V84's augmentation; the other tests zero optical PSFs, weak synthetic
textures, photographic contrast attenuation and reviewed fine-detail ROIs.
The architecture, broad flat palette, native128 and paired32 targets stay fixed.
See the [recipes, execution status and evaluation approach](quality-first-training.md).
V101 reaches **36.50347dB** on full427, +.06351dB over V84, improving 418/427
source means and all seven condition means. Known/unseen CFA means remain close
to V84. The [completed primary report](v84-curated-quality-review.md) and
[current native gallery](heldout-detail.md) show gains and remaining smoothing.
V101 is the next training checkpoint in V84’s architectural family.

The source scan covers88,508 training images, with570 actually reviewed and 31
withheld/excluded. Completed runs used the earlier 24 exclusions; seven more and
a 32-region detail catalogue are prepared for the next 88,477-source cohort.
The [illustrated source review](corpus-source-review.md) explains why
processing defects/nonphotographic targets are removed while difficult foliage,
textiles and weak real detail remain. Originals and historical manifests stay
read-only; protected captures and the GFX scene/siblings remain outside training.

Earlier [V93–V95](v43-curated-original20k-review.md) showed cleaner-data and
weak-detail gains on the older ViT-S model. [V96/V97](v95-flat-palette-quality-review.md)
and [V98/V99](v95-adc-training-quality-review.md) expose palette/ADC tradeoffs.
The complete reports retain favorable and adverse results. They do not require
using V43 as today's baseline.

[Reviewed corpus](commons-post4557-reviewed.md) ·
[Archive status](commons-download.md) ·
[Augmentation and selected-domain loading](training-pipeline.md) ·
[Native targets](public-raw-expansion-v2.md) ·
[Source/series exclusions](commons-content-overlap.md).

## Reading the evidence

Current guides and README images reflect useful available implementations.
Versioned reports retain the experiments' numerical results and protocols;
original decisions and chronology remain in the timestamped [diary](../diary/index.md).
Source/scene intervals describe the sampled cases, not training-seed uncertainty.
Real AHD/separate ISO100 references are not exact GT.

[Full-frame RGB16 measurements](mature-cudnn-fullframe.md) remain specific to
their checkpoints. Quality has priority over further speed work.
[Documentation guide](index.md) · [Research](research.md) ·
[Remaining project goals](requirements.md).
