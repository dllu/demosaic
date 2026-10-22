# Quality training on the V84 baseline

**Use V84's DRUNet RGB trunk and frozen DINOv3 ConvNeXt-Tiny feature pyramid
as the development baseline.** V84/V85 provide the strongest completed full-photo
scores and useful image quality. V43 remains a historical comparator;
[current models and native examples](current-model.md) explain the choice.

## Current comparison

Two continuations start from the exact final V84 EMA with fresh AdamW/EMA:

| Setting | V100 control | V101 fine-detail recipe |
| --- | --- | --- |
| Commons training pool | Curated 88,484 | Same |
| Native / paired targets | Original 128 / 32 | Same |
| Optical PSF probability, Commons and native | .25 | 0 |
| Synthetic share of Commons-domain samples / weak subset | .20 / 0 | .20 / .15 |
| Photographic contrast attenuation probability | 0 | .25 |
| Reviewed ROI probability, conditional on a photographic Commons sample | 0 | .05 |
| Flat palette | Original V84 .10 share /8 chroma stops | Same |
| Learned architecture / initializer | V84 final20k | Same exact weights |
| Schedule | Seed59, B16/native256, BF16,10,000 updates, LR3e-6/warmup100 | Same |

[Control recipe](../configs/quality-v84-curated-control-v100.yaml) ·
[Fine-detail recipe](../configs/quality-v84-fine-detail-v101.yaml).
The second arm tests the complete fine-detail package. Its result will not
attribute a gain to one component in isolation. Keeping V84's broad palette
avoids inheriting the narrower color distribution of the recent ViT-S runs.

The `.15` weak subset is 15 percentage points of Commons-domain samples,
roughly 75% of their synthetic component. It is about 7.5% of all training
examples after domain selection. The `.05` reviewed-ROI probability is
conditional on a photographic Commons sample, about 1.8% of all examples.
[Exact seed59 schedule counts and actual clean-target views](training-pipeline.md#current-recipe-sampling-and-targets)
make these different denominators explicit.

Both use 4× caches, geometry before final area2 reduction, selected-domain loading,
the unchanged physical noise priors, sensor-valid camera supervision and
Charbonnier reconstruction. The native/paired fractions stay .25/.25. The six
reviewed ROIs are existing training sources; oversampling their selected
structures changes source/field-of-view frequency rather than adding new IDs.
The [reader validation](training-pipeline.md#reviewed-photographic-regions) records
hash, bounds, augmentation-order and resume checks.

## Data and source quality

The current cohort has 88,484 Commons training sources, versus 84,867 in V84's
original recipe. It preserves the same 2,303 validation and 2,255 test memberships.
The full source scan covered 88,508 training images. The active cohort applies
24 visual exclusions. Targeted review now covers 570 sources: 539 retained and 31
withheld/excluded. Seven additional exclusions are prepared in a separate
88,477-source follow-up; the completed runs keep their frozen inputs. Its
[expanded 32-region catalogue](../configs/low-contrast-training-rois-curated-v3.json)
preserves the original six and adds 26 reviewed fine-detail sources for a future
experiment. [Data, native examples and reader proof](results/source-quality-detail-catalogue-v3.json).
High loss, ISO and metadata selected review candidates; visible native/binned
quality determined exclusions. Hard
foliage, textiles, nets, weak fog and other useful detail remain eligible.
This is targeted inspection, not a claim that every source was manually viewed.

[Illustrated source review](corpus-source-review.md) ·
[Curated manifests and membership checks](results/v43-quality-curation-and-training-plan-v1.json) ·
[Reviewed texture catalogue](../configs/low-contrast-training-rois-v1.json).
The GFX train/platform scene, its siblings and other protected evaluation
captures stay outside training. Originals stay read-only; cached source data
and frozen manifests avoid source HDD reads during these runs.

Source selection draws with replacement, so pool size differs from exposure in
one continuation. The fixed10k schedules contain55,843 photographic Commons
examples each, among160,000 total training examples:

| Full scheduled endpoint | V100 | V101 |
| --- | ---: | ---: |
| Unique photographic sources | 41,379 | 39,838 |
| Unique sources newly eligible since original V84 | 1,686 | 1,631 |
| Examples from those newly eligible sources | 2,291 | 2,168 |
| Reviewed ROI examples | 0 | 2,844 |

The current pool adds3,640 eligible source IDs and removes23 relative to V84's
original84,867; an [explicit exclusion-set check](results/training-v100-v101-source-exclusion-set-v1.json)
shows that one of the24 visual exclusions was already outside that earlier
pool. V101 reallocates some ordinary-photo draws to the six reviewed ROIs.
These reconstruct the complete fixed10k schedules; both trainers have now
finished. The [source-coverage audit](results/training-v100-v101-source-coverage-v1.json)
reconciles the earlier kind/ROI counts and checks24 actual reader source paths.
Keep the current endpoints fixed; consider these exposure counts alongside the
quality results when choosing a later training budget.

## Execution and evaluation

The source-frozen runner executes discarded eight-update 64×64 CPU/B1 and
CUDA256/B16 smokes for each recipe, then starts each production run freshly from
V84. It checks exact initial EMA/DINO identities, finite states and expected
update counts. Available RAM must stay at least 48GiB for 15s before each worker;
the trainer checkpoints/stops below 24GiB, and CUDA allocation is capped at 24GiB.
Root/external startup reserves are 32/256GiB, comfortably above this study's
few-GiB planned footprint. Only owned workers are managed; failures are preserved
without automatic retries.

Frozen plan: `.cache/current-quality-20261022-v1/training-v2/plan.json`.
Runs: `/mnt/external/demosaic/v84-curated-quality-20261022-v2/`.
All four discarded CPU/CUDA smokes passed, and both production runs completed
10,000 updates from the same exact V84 weights. Both original trainers/controllers
have exited. Actual owner/phase status is in the local `status.json`.
The [complete V84/V100 CPU camera comparison](real-camera-quality.md) is available:
a small known-camera gain and unseen-camera loss, with close native outputs.
The broader V84/V100/V101 photographic/camera study is now running.
[Original launch and verification](results/current-model-baseline-selection-v1.json).

The [supplementary CPU report](results/heldout-detail-V101-final-v1.json) compares
V101's final10000 EMA on the same12 cached bark/feather/canopy/fur observations
as V84/V100. It verified the finished endpoint/hash, used the original frozen
reporter with two CPU threads and no GPU, and produced12 new native triplets.
All72 cells of the three updated boards were inspected. V101 gains PSNR on all12
selected cases against both V84/V100, with smaller high-noise gains and remaining
fine-detail smoothing. This is four-source evidence, separate from the panels
below. Its [queue record](results/V101-natural-detail-queue-v2.json) preserves
the original execution setup.

The evaluation queue at
`.cache/current-quality-20261022-v1/evaluation-queue-v1/` has started the seven
panels below after both original training owners exited. It compares V84 with
the final V100/V101 EMAs under the same IEEE FP32 observations and includes
RawNIND where applicable. Outputs go to
`/mnt/external/demosaic/v84-curated-evaluation-20261022-v1/`.
The three-model workflow previously passed a CPU reporting smoke with72 cases
and six actually viewed native triplets; production results follow separately.
[Evaluation readiness](results/v84-recipe-evaluation-readiness-v1.json).

The full-frame queue at `.cache/current-quality-20261022-v1/fullframe-v1/`
then restores the complete GFX scene with V84, both final continuations and
RawNIND-channel. It exports RGB16 files and six fixed native crop comparisons;
the [GFX guide](gfx-qualitative.md) records the settings. This queue also waits
for the preceding controller to exit before launching a GPU worker.

Compare new checkpoints with V84 and useful alternatives on full 427-photo,
known/unseen measured-CFA, weak-detail/color and standing GFX tests. Show at
least two unchanged native noisy/restored/GT triplets per reported model, with
coordinates, checkpoint hash, noise and display metadata. Real ISO 100/AHD
references remain accurately labeled as nonexact.

The [natural-detail gallery](heldout-detail.md) fixes four held-out contexts
before viewing these model outputs: pale bark, white feathers, forest canopy
and gray fur. Shared cached observations at ADC-only, ISO100 and ISO12800
give a matched visual comparison of both completed continuations.
V101 gains .155/.110/.017dB over V84 on these selected
ADC-only/ISO100/ISO12800 interiors, versus V100's .076/.062/.007dB.
The images remain close and retain high-noise texture loss. This supplementary
diagnosis does not replace the full panels above;
[V101 per-case evidence](results/heldout-detail-V101-final-v1.json) records the
gains and remaining chroma/gradient tradeoffs.

Report source/scene intervals, adverse cases and the selection of any displayed
checkpoint. Choose useful versions from overall metrics and actual images;
one small diagnostic loss or an interval crossing zero does not forbid using
a better architecture or updating current documentation. Reserve stronger
claims such as SOTA, broad real-camera superiority or a particular full-frame
runtime for evidence covering those claims. Quality remains the priority.

## Earlier evidence that informs this work

[V84/V85](native-data-original20k-review.md) improve photographic quality while
the extra 22 native captures have little matched effect. The
[V93–V95 cleaned-data/augmentation comparison](v43-curated-original20k-review.md)
finds photo/weak-detail gains on the older ViT-S architecture, with remaining
color shifts. [V96/V97](v95-flat-palette-quality-review.md) and
[V98/V99](v95-adc-training-quality-review.md) expose further palette/ADC tradeoffs.
Those are useful observations, not reasons to keep the global baseline at V43.
Immutable receipts retain original study decisions; the timestamped
[diary](../diary/index.md) preserves the chronology.
