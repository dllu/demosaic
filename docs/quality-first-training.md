# Quality training in the V84 architectural family

**Continue quality work from V102 final20k in V84's DRUNet RGB/frozen DINOv3
ConvNeXt-Tiny family.** It reaches36.67951dB photographic PSNR,+.17604dB over
V101, with higher known/unseen CFA means. V103 is a close alternative; V102's
flat-color and weak-texture diagnostics favor it overall. High-noise fine detail
remains soft. [Completed results and native comparisons](v102-v103-quality-review.md).

## Completed matched comparison: V102/V103

Both runs continue the exact final V101 EMA on the newly frozen 88,477-source
cohort, with fresh AdamW/EMA. They retain the zero-PSF, weak-texture and
photographic contrast package. The only recipe difference is **six versus 32
reviewed source regions**, both sampled at 5% conditional on a photographic
Commons example. The six-region control preserves the original ROI objects
while rebinding to the same new manifest.

| Shared setting | Value |
| --- | --- |
| Parent | V101 final10000 EMA |
| Commons cohort / visual exclusions | 88,477 /31 |
| Native / paired captures | 128 /32 |
| Schedule | Seed60, 20,000 updates, B16/native256, BF16 |
| LR / warmup | 1e-5 /200 updates |
| V102 reviewed regions | Original 6 |
| V103 reviewed regions | Expanded 32 |

[Six-region recipe](../configs/quality-v101-detail-six-v102.yaml) ·
[Expanded recipe](../configs/quality-v101-detail-expanded-v103.yaml) ·
[Actual launch and discarded CPU/CUDA checks](results/v101-detail-diversity-training-launch-v1.json).
All four discarded eight-update CPU/CUDA checks passed from exact V101 weights
with finite states and unchanged official DINO. Both original20k production
endpoints, all seven evaluation panels and complete GFX exports have completed
successfully. Owners exited; no intermediate checkpoint search selected them.

V102/V103 photo PSNR is36.67951/36.68091dB. V102 gains+.17604dB over V101
on full427, with425 source means improving; known/unseen CFA means rise to
54.23709/53.97177dB. The six/32 ROI difference has only a tiny photo effect,
while V102 has lower ADC color bias and stronger tested weak-carrier response.
Use V102 as the next initializer. [Scores, uncertainty, actual native review
and hashes](v102-v103-quality-review.md).

The [four-material CPU panel](heldout-detail.md) separately shows V102's
+.362/+.285/+.043dB ADC/ISO100/ISO12800 gain over V101 and all12 improved
PSNR/SSIM/chroma/gradient cases. The [completed V103 material follow-up](heldout-detail.md#v102-versus-v103-on-the-fixed-material-panel)
is slightly lower than V102 on its four-source condition means, with close native output.
The [current GFX gallery](gfx-qualitative.md) now uses completed blended102MP
outputs for V101/V102/V103/RawNIND; older512CPU contexts remain linked.

Frozen roots under`.cache/current-quality-20261022-v1/`:
`detail-diversity-training-v1/`,`detail-diversity-evaluation-v1/`,
`detail-diversity-fullframe-v1/`. Corresponding artifacts under
`/mnt/external/demosaic/` are`v101-detail-diversity-20261022-v1/`,
`v101-detail-diversity-evaluation-20261022-v1/` and
`v101-detail-diversity-fullframe-20261022-v1/`. Original pending-status receipts
and code snapshots remain unchanged; the
[completion receipt](results/v102-v103-quality-complete-v1.json) closes the review.
All48 numerical modules match between arms; the archive hash differs solely
because the reviewed-ROI catalogue is frozen with the recipe.

## Active V104 cleaned-corpus continuation

**V104 production training is running** from exact V102 final20k EMA on the
reviewed **90,872-source**4×/8× pair. Both discarded eight-update CPU and
CUDA checks passed, verifying exact parent EMA initialization,finite states
and unchanged official DINO. The original20k production run starts freshly
again with AdamW/EMA,seed61,B16/native256/BF16,LR1e-5/warmup200. Its six original
ROI objects and5% conditional-photo probability,zero optical PSFs,weak synthetic
textures,photo contrast attenuation,native128/paired32 remain unchanged.

[Recipe](../configs/quality-v102-reviewed-corpus-v104.yaml) ·
[Six-ROI binding](../configs/low-contrast-training-rois-six-reviewed90872-v4.json) ·
[Actual launch,discarded smoke/report proof and source exposure](results/v104-reviewed-corpus-training-launch-v1.json).
V102 remains the recommended inference checkpoint; V104 has no production
quality result yet. More training,seed and data change together,so any gain
cannot be attributed solely to the larger corpus.

The fixed20k schedule contains113,058 photographic examples,62,976 unique
photo sources and2,811 draws from1,645 newly eligible sources. Its5,672 reviewed
ROI draws cover the same six sources. These are reconstructed full-schedule
counts,not a claim that training has finished. Twelve actual clean-reader
checks cover six new-source draws and all six ROIs,repeated exactly with
finite native256 outputs and unchanged Torch RNG,no GPU or denoiser.

Full427/16procedural/seven-condition/four-CFA,known4/unseen5 measured-camera,
weak texture,color,GFX and highlights are queued after the exact original
trainer/controller exits. Complete102MP RGB16 exports follow evaluation. A separate CPU-only queue will
compare the original final V104 EMA with V102 on all 12 fixed material cases,
using current frozen source and exactly replayed observations after the trainer exits.
A discarded CPU reporting integration already passed60 case rows/four triplets;
all eight unique native board cells were actually viewed. It checks reporting,
not model improvement. The new cohort preserves2,303 validation/2,255 test
memberships and all protected scene exclusions.

Local frozen roots under`.cache/current-quality-20261023-v1/`:
`reviewed-corpus-training-v1/`,`reviewed-corpus-evaluation-queue-v1/`,
`reviewed-corpus-evaluation-v1/`,`reviewed-corpus-fullframe-v1/`.
Artifacts under`/mnt/external/demosaic/`:
`v102-reviewed-corpus-20261023-v1/`,
`v102-reviewed-corpus-evaluation-20261023-v1/`,
`v102-reviewed-corpus-fullframe-20261023-v1/`.
Startup floors are48GiB RAM,32GiB root and256GiB external free space;
trainer stops below24GiB available RAM and CUDA allocation is capped at24GiB.
Failures are preserved without automatic retry. Quality remains the priority.

The2,395 eligible arrivals and five optional fine-detail sources are documented
in the [incoming source review](incoming-commons-quality.md). The earlier
six/32 ROI comparison had little photographic effect; retain the simpler six
before adding another ROI intervention.

## Prepared Tiny/Small quality comparison

[V109 Tiny](../configs/quality-v102-backbone-tiny-v109.yaml) and
[V110 Small](../configs/quality-v102-backbone-small-v110.yaml) recipes are frozen
for a matched 20,000-update comparison on the separate **90,864-source** corpus.
Both load one V102-derived initializer file with three zeroed fusion-gate
tensors; the other 88 EMA tensors remain exact. This gives the encoders a common
initial function while allowing their fusion to adapt during training. Only
the official frozen encoder name/revision/hash differs between arms. Both use
seed 62, batch 16, native 256-pixel patches, BF16, learning rate 1e-5, 200 warmup
updates, zero optical blur and the original six ROIs.

The corpus applies eight additional visually inspected withholds relative to
V104: three degraded photo targets and five atlas reproductions. Four atlas
sources were in the older V102 corpus; 2,391 new arrivals remain eligible.
Validation/test and protected-source boundaries remain fixed. Twelve actual
clean-reader examples repeat exactly: six new-source draws and all six ROIs.
The full prospective schedule contains
111,559 photo examples from 62,367 unique sources, including 2,707 draws from
1,634 newly eligible sources and 5,657 ROI examples. These are scheduled exposure
counts, not completed training. [Prepared plan, hashes and reader evidence](results/backbone-capacity-training-prepared-v2.json).

No production controller has launched for these recipes.
The incoming loss-tail review is complete. Complete and review V104 first;
retain the prepared evidence if later results warrant a different initializer
or cohort. The earlier unlaunched V107/V108 preparation remains preserved.
The [fixed-reference configuration](../configs/quality-v102-backbone-reference-checkpoints-v1.json)
and [validated reporting/export support](training-execution.md#fixed-references-alongside-derived-initializers)
keep original V102 separate from the zero-gate derivative. Separate discarded
eight-update CPU checks now pass for both cleaned recipes, with exact initial
EMA/encoder identities, finite final model/EMA/Adam and identical eight-batch
observations across all three data domains. [Actual CPU evidence](results/backbone-cleaned-recipes-CPU-v1.json).
Fresh eight-update CUDA checks now pass at native256/B16/BF16. Initial EMA and
per-arm encoder identities match; all eight actual observations and the first
loss agree across arms, and model/EMA/Adam remain finite.
[Actual CUDA evidence](results/backbone-cleaned-recipes-CUDA-v1.json).
These are discarded fixtures. Review V104 before selecting the production
initializer, then compare final native photo/material/color/weak-detail/GFX
outputs before drawing a capacity conclusion.
[Capacity evidence and remaining work](convnext-small-capacity.md).

The [fixed-output loss-smoothing diagnostic](loss-smoothing-detail.md) measures
whether a smaller Charbonnier scale strengthens faint-detail supervision.
It motivates a separate later training comparison. The current trainer now
exposes [validated reconstruction epsilon](loss-smoothing-detail.md#configurable-training-scale),
with exact default replay and nondefault resume checks. Current recipes retain
the original loss alongside their fixed data and encoder settings.

## Completed V100/V101 comparison

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
The second arm tests the complete fine-detail package. Its gain does not
attribute an effect to one component in isolation. Keeping V84's broad palette
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

V104 uses the reviewed **90,872-source**4×/8× pair. The next prepared capacity
recipes use **90,864 sources**, applying eight additional withholds relative to
V104 while preserving earlier exclusions and unchanged 2,303 validation/2,255
test memberships. The 2,395-source loss screen is complete, with all 74 final
ranking candidates inspected at their scored native coordinates. Targeted
native inspection of the arrivals now covers 153 unique identities. Five atlas
reproductions are withheld after source-credit and native-view checks; real
photographed-window controls remain eligible. This is targeted inspection,
not exhaustive manual quality review.
Native source comparisons, corpus bindings and actual reader checks are in the
[incoming source review](incoming-commons-quality.md). Existing experiment
manifests and machine receipts retain their original bytes.

The completed V100/V101 cohort has 88,484 Commons training sources, versus 84,867 in V84's
original recipe. It preserves the same 2,303 validation and 2,255 test memberships.
The full source scan covered 88,508 training images. That cohort applies 24 visual exclusions. Targeted review now covers 570 sources: 539 retained and 31
withheld/excluded. Seven additional exclusions are applied to the separate
88,477-source V102/V103 cohort; V100/V101 keep their frozen inputs. Its
[expanded 32-region catalogue](../configs/low-contrast-training-rois-curated-v3.json)
preserves the original six and adds 26 reviewed fine-detail sources for V103. [Data, native examples and reader proof](results/source-quality-detail-catalogue-v3.json).
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
The [completed V84/V100/V101 primary report](v84-curated-quality-review.md)
includes full427 photographic and known/unseen measured-CFA results, independently
rebuilt source means, intervals and native crops. All seven evaluation panels
and the complete GFX exports have finished; [full-frame results](gfx-qualitative.md)
include native crops and checkpoint-specific timings.
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
`.cache/current-quality-20261022-v1/evaluation-queue-v1/` completed all seven
panels after both original training owners exited. It compares V84 with
the final V100/V101 EMAs under the same IEEE FP32 observations and includes
RawNIND where applicable. Outputs go to
`/mnt/external/demosaic/v84-curated-evaluation-20261022-v1/`.
The three-model workflow previously passed a CPU reporting smoke with72 cases
and six actually viewed native triplets; production results follow separately.
[Evaluation readiness](results/v84-recipe-evaluation-readiness-v1.json).

The completed full-frame queue at `.cache/current-quality-20261022-v1/fullframe-v1/`
restored the complete GFX scene with V84, both final continuations and
RawNIND-channel. It exported RGB16 files and six fixed native crop comparisons;
the [GFX guide](gfx-qualitative.md) records the settings. It waited
for the preceding controller to exit before launching its GPU worker.

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
