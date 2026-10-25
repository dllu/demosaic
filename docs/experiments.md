# Experiment index

**V114 Tiny is the current general baseline in V84's architectural family.**
Its full-photo mean is36.97973dB, +.07735 over V112, with422/427 source means
rising. V115 fitted Small has higher known-camera quality and eight-pixel weak
response, while Tiny has slightly higher photo PSNR and lower color bias.
[Completed panels, native comparisons and full exports](v114-v115-quality.md).
Fine foliage/neon and dark-camera mottling remain weak. [V116 is training](fine-detail-data-training.md)
to test fine weak sources and reviewed reference masks against matched V114.
The [current V114 eight-view pilot](v114-eight-view.md) improves all12 fixed
material cases and both selected camera crops, with a small selected color-bias
tradeoff; independent/native review is complete and full panels/frame remain
unmeasured. The earlier [V112 eight-view pilot](v112-eight-view.md) retains its explicit
weights and unmeasured full-panel/frame scope.

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
| Native data and larger context | V84/V85 establish the36.44dB architectural reference continued by V101. The extra native captures have little matched effect; larger context is a separate small-effect comparison | [V84/V85](native-data-original20k-review.md), [V86/V87](training-context-original4k-review.md) |
| Spectral and late RGB refinement | Small matched mean gains or protected common weights did not fix weak detail; head-only V92 regressed | [V88/V89](spectral-original4k-review.md), [V90/V91](late-rgb-original4k-review.md), [V92](late-rgb-head-only-original4k-review.md) |
| ADC-only inference | With unchanged V104 weights, replacing only valid measured sites gains .2885 dB rendered PSNR across all 427 sources/all 1,708 CFA cases. Local chroma/SSIM regressions and a flat-color tail remain; positive-noise profiles bypass it | [Complete site-consistency comparison, actual export and native crops](adc-consistency.md) |
| Eight-view inference | Full427 photo PSNR37.04376dB; all 427 source means and4/4 known,5/5 unseen scene means improve over V104 single. ADC tail420.90DN16 remains worse than V112, with fine-detail/blotch weaknesses. Costs eight evaluations per tile | [Full panels, native examples and independent audit](dihedral-quality.md), [complete-frame comparison](dihedral-fullframe.md) |

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
V101 reaches **36.50347dB** on full 427, +.06351dB over V84, improving 418/427
source means and all seven condition means. Known/unseen CFA means remain close
to V84. The [completed primary report](v84-curated-quality-review.md) and
[current native gallery](heldout-detail.md) show gains and remaining smoothing.
V102/V103 completed their20k six/32-region comparison on88,477 sources. All seven
evaluation panels and full-frame exports finished. V102 improves425/427 source
means over V101; the six/32 ROI effect is small and mixed across diagnostics.
[Completed current results](v102-v103-quality-review.md). V104 completed 20k
from V102 on 90,872 sources with 2,395 eligible additions. It improves PSNR,
SSIM and gradient error in all 12 selected material cases; [native comparisons](heldout-detail.md)
are current; all seven evaluation panels and full-frame exports are complete.
[Source review and native examples](incoming-commons-quality.md).
The [complete paired training-reference audit](paired-reference-quality.md)
also prepares a narrow opt-in mask revision for two recurring red-speck
references, preserving useful flagged texture and the active data bindings.
The [completed V111/V112 loss-scale comparison](loss-scale-training.md)
uses the cleaned90,864-source corpus and original V104 EMA/gates. Both add about
.10dB on full427; V112 improves camera/color over V111 and supplies the
parent of current V114. The [primary report](v111-v112-primary-quality.md) and
[complete review](v112-quality.md) show native strengths and remaining limits.
The [completed Small transfer](small-feature-transfer.md) now uses V112 teacher
targets and cached training features. Photo means remain close, while two dark
camera crops lose .20–.32dB. Matched Tiny V114 / fitted Small V115 passed eight
actual CPU/CUDA updates each; [both have completed 20,000 updates](small-aligned-training.md).
[Complete quality review](v114-v115-quality.md) now selects Tiny for general
photo/color balance while documenting Small's known-camera/eight-pixel gains. The old idle V113 plan and evidence remain preserved.
Their [endpoint evaluation queue](quality-prediction-archive.md) retains exact
targets and native predictions across all numerical panels, with standing GFX
contexts and complete-frame exports; existing controls are reused.

The [clean-target frequency audit](fine-weak-texture-coverage.md) finds a narrow
gap in dedicated weak textures, while sampled photo/native targets contain
fine-frequency energy. The optional fine profile passes reader and actual V112
CPU training checks but has no trained-quality result and does not change the
active comparison.
The [V116 trial](fine-detail-data-training.md) is now training after that review,
combining the fine profile and reviewed paired masks while reusing completed
V114 as its matched Tiny control. Native256 mask-path/source/loss and actual
CUDA checks pass. Single-candidate evaluation and independent review are queued too.

The source scan covers88,508 training images, with570 actually reviewed and 31
withheld/excluded. Completed runs used the earlier 24 exclusions; seven more and
a32-region detail catalogue are used by V102/V103 on the separate 88,477-source cohort.
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
