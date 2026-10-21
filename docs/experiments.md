# Experiment index

**V43 step 2000 is the working reference.** Aggregate photo PSNR has increased
in later experiments, but fine-detail loss, color artifacts and camera
tradeoffs have prevented a convincing replacement. The next work keeps V43's
architecture and changes data quality and augmentation, before pursuing speed.

[Current quality plan](quality-first-training.md) ·
[PSNR history and complete point table](performance-history.md) ·
[representative native crops](../README.md#current-100-crops) ·
[complete chronological experiment archive](experiment-archive.md).

![PSNR history](images/version-PSNR-history.png)

The plot reuses completed primary evaluations. Architecture, data, initialization,
training horizon and recorded precision differ across versions. Higher means
alone do not establish better low-contrast detail or statistically significant
camera gains. Every plotted checkpoint and source report is linked in the
[history data](results/version-PSNR-history.json).

## What the main experiment families established

| Family | Main finding | Evidence |
| --- | --- | --- |
| Geometry and original V43 | Geometry/PSF before the final 2× reduction helped the matched photo test. Diverse native targets and the full-resolution RGB/DINOv3 ViT-S model produced the current reference | [V34/V36](geometry-corpus-v34-v36-review.md), [V43 step 2000](native-corpus-2k-review.md) |
| Larger Commons corpus and longer training | Larger data helped average photo PSNR modestly in the ConvNeXt comparison, without resolving detail/color limitations | [V63/V64 original20k](long-commons-v63-v64-original20k-review.md) |
| Color coordinates and supervision | Normalization, objective and camera-supervision changes produced tradeoffs | [V68/V69](normalization-v68-v69-original4k-review.md), [V74/V75](reconstruction-objective-first1k-review.md), [V76/V77](camera-supervision-first1k-review.md) |
| Compact RAW-native architecture | The completed mixed-batch experiment remains far below the mature RGB models on primary panels | [V72/V73](packed-isotropic-mixed16-quarter-review.md) |
| Directional, interval and bank heads | Higher photographic means coexisted with failed camera/detail criteria | [V78/V79](directional-interval-original4k-review.md), [V80/V81](directional-bank-original4k-review.md), [V82/V83](bank-detachment-original4k-review.md) |
| Native data and larger context | The tested expansion and context changes did not supply the desired matched improvement | [V84/V85](native-data-original20k-review.md), [V86/V87](training-context-original4k-review.md) |
| Spectral and late RGB refinement | Small matched mean gains or protected common weights did not fix weak detail; head-only V92 regressed | [V88/V89](spectral-original4k-review.md), [V90/V91](late-rgb-original4k-review.md), [V92](late-rgb-head-only-original4k-review.md) |

Each complete quality review retains source/checkpoint identities, native
noisy/restored/reference crops and explicit real-reference limitations. The
[chronological archive](experiment-archive.md) preserves the longer record,
including early versions, negative studies and engineering details.

## Data and current quality work

The completed scan covers 88,508 training sources at 4×/8×. Targeted visual review
of 371 sources withholds 24 while retaining legitimate difficult detail. The
frozen matched V43 study uses 39,983 control / 88,484 larger training sources;
all six fresh CPU/CUDA preflights passed, all three arms completed 20k with
independent saved-state audits, and the full matched evaluation/native review is
complete. The [V93–V95 review](v43-curated-original20k-review.md) finds photo and
weak-detail gains with remaining saturated-color/unseen-camera tradeoffs.
The [V96/V97 follow-up](v95-flat-palette-quality-plan.md) keeps that weak-detail
recipe and tests a wider colored-flat palette from V95; quality results remain
pending.
Originals and historical manifests remain read-only. Validation/test and the
standing GFX scene remain outside training. See the [source review](corpus-source-review.md).

[Reviewed corpus](commons-post4557-reviewed.md) ·
[archive status](commons-download.md) ·
[augmentation and selected-domain loading](training-pipeline.md) ·
[native RAW targets](public-raw-expansion-v2.md) ·
[source/series exclusions](commons-content-overlap.md).

## Engineering record

The project can restore full 102 MP captures and export checked16-bit TIFFs.
Earlier [FP32 timing/export validation](mature-cudnn-fullframe.md) and the
[stopped FP16 qualification](mature-hidden-FP16-full-quality.md) remain documented.
The new fixed-backend speed study was prepared but **not launched**; quality
work now takes priority. There is no new speed/default or quality promotion.

[Documentation guide](index.md) · [research](research.md) ·
[completion evidence](requirements.md) · [local-time diary](../diary/index.md).
