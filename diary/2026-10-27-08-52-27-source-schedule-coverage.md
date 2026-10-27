# Photographic source coverage and current pipeline documentation

Recorded: 2026-10-27T08:52:27-07:00 (America/Los_Angeles).

The preceding goal turn made progress: `bc3e3a8` published40 actual source
reviews and the prepared90780/31 data. This turn verifies the exact live V124
worker and waiting spatial/progress owners, then measures a distinct remaining
quality question: how much of the larger corpus a finite training run visits.

The actual metadata audit stops the real reader before source pixels or
procedural generation at159,088 V124 and160,736 V131 Commons indices. An
independent selector agrees on every source/family/ROI decision and complete
local RNG state. Independent domain decisions agree at all40,000 planned steps.
The relevant reader/scheduler ASTs match each original executed/queued source.
The genuine constructors check20+29 reviewed caches/crops/area2 targets before
the stop hooks; overlapping sources are checked in each catalogue. This is
metadata source selection, not a replay of old augmentation or neural work.

V124's frozen trace prefix through7,600 contributes480 actual first-view records,
all matching. The full20k schedules remain prospective. V124, seed67/fraction.05,
selects111,410 photos including5,602 reviewed draws, covering62,548/90,784 sources
(68.897603%). The spatial recipe, seed70/fraction.5, selects112,424 photographs
including56,256 draws across29 reviewed regions. It visits42,086/90,781 sources
(46.359921%), with1,848–2,031 reviewed draws per source.

On that same spatial cohort/seed/budget, a metadata-only fraction.05 alternative
would visit62,872 sources (69.256783%), with5,601 reviewed draws and165–221 per
region. Quotas0/.05/.1/.25/.5 are recorded for both schedules. Source identity
repetition can include different geometry, contrast, camera and noise; these
counts establish concentration rather than overfitting or quality gains.
A lower-quota quality comparison at fixed architecture/data is the next data
hypothesis; original running/queued recipes remain fixed.

Independent Python aggregation reopens all319,824 saved per-index CSV rows and
reproduces actual families, unique sources, reviewed counts and visited/unvisited
histograms. All ten quota summaries reconcile. Global Python/NumPy/Torch RNG
states stay unchanged and CUDA stays uninitialized. There are zero new training
targets, geometry augmentations, neural forwards, sensor-noise observations,
RAW decodes or optimizer updates. No new model score or performance-history point.

The standalone PNG/SVG and public ten-row CSV summarize the existing audit.
Both initial and final renders were actually viewed. The final title says
"clean target slots" to avoid implying globally unique photographs. Initial
reporter/receipt/figure bytes are preserved under `initial-render-v1` and the
original frozen reporter; only reporting was rendered again, with no reader
or model repetition. All original audit and machine-receipt bytes remain.

Evergreen `current-model.md` and `training-pipeline.md` now describe current
choices, sampling probabilities, completed/queued trials and useful limits.
Stale V122/V123-active and untrained14-region descriptions are removed from
these current guides; historical details and the exact previous pages follow.
README/research/requirements/source and contrast guides link the new coverage
finding. Current V120 selection, all56 plot points, GFX sources/references,
originals and all active source/config/checkpoint/forward budgets stay unchanged.

Artifacts are under
`.cache/current-quality-20261023-v1/source-schedule-coverage-v1/`:
`plan-v1.json`, `run/result-v1.json`, both full metadata CSVs,
`verification-v1.json`, frozen `work/` sources and `initial-render-v1/mapping-v1.json`.
Public results are `docs/results/training-source-schedule-coverage-v1.json` and
`.csv`; the report is `docs/training-source-schedule-coverage.md`.

Final publication verification passes184 local links, five inbound guide anchors,
980 frozen input/source bindings across nine plans, and seven exact live
controller identities. Public recipe scheduling matches the frozen spatial
production recipe, and both spatial arms share that source schedule. Ruff and
format checks pass for both new scripts. The publication-only checker preserves
its initial schema-assumption failure, then supports both `plan` and `queue_plan`
status formats; no reader or model work is repeated.

## Exact previous current-model.md

SHA256: `d67ad9be2ed52edd5fd317cea610cafc85a4996646cdd02d9a97e6139a1a7bda`.

````markdown
# Current model choices

**V120 Small is the current general restoration and quality-development recommendation.**
Its primary panels, native synthetic triplets, full local statistics and selected
native review are complete. Photo37.04008dB and known/unseen54.31272/54.00872dB
coexist with a much lower tested ADC maximum than V119:55.52DN16.
[Matched-profile full-frame comparisons](v120-v121-primary.md#matched-profile-full-frame-gfx)
against V115/V119 are complete; differences remain subtle and fine detail stays soft.
[V120/V121 measured gains and remaining limits](v120-v121-primary.md).
Quality development uses the Small architecture; active V122/V123 keep their
fixed V115 parent for the controlled frequency-scope comparison.
V114's full-photo mean is36.97973dB, +.07735 over V112, with422/427 photo-source
means improving. Complete primary/analytic panels, independent saved-output
metrics, native review and102MP RGB16 exports are verified.
[Full Tiny/Small comparison](v114-v115-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General RAW and quality development | **[V120 Small](v120-v121-primary.md)**: photo37.04008dB; known/unseen54.31272/54.00872dB; ADC maximum55.52DN16; recovers V119 camera/color regressions. Remaining mesh softness and GFX profile-comparison limits are explicit |
| Fully reviewed Tiny alternative / lower tested ADC maximum | **V114 Tiny**: photo36.97973dB; known/unseen CFA54.28627/54.00290dB; ADC mean/max bias7.08/51.73DN16 |
| Higher single-view photo score | **[V117 Tiny](v117-v118-quality.md)**: photo37.04408dB, +.06435 over V114; camera54.27303/53.97339dB and ADC max63.89DN16; remaining fine-detail softness |
| Higher measured known-camera mean / eight-pixel weak response | **V115 fitted Small**: photo36.97700dB; camera54.32405/54.00417dB; ADC max65.64DN16 and high-noise max106.79 versus Tiny85.40 |
| Optional eight-view V114 inference | [Fixed24 pilot](v114-eight-view.md): all12 material cases and both selected adverse camera crops improve; selected color bias rises slightly while spatial variation falls. Real fine detail remains soft; full panels/frame unmeasured; eight evaluations per tile |
| Exact parent and previously measured optional modes | [V112](v112-quality.md): photo36.90238dB, ADC maximum50.89DN16; [eight-view fixed24 pilot](v112-eight-view.md) improves all12 material cases, but full panels/frame remain unmeasured |
| Earlier full-panel eight-view option | [V104 dihedral8](dihedral-quality.md): photo37.04376dB, camera54.33283/53.99412dB; worse ADC maximum420.90DN16 and unresolved fine detail; eight evaluations per tile |
| Explicit ADC observed-sample fidelity | [V114 sites export](adc-consistency.md): ADC photo 37.78013→38.01575dB across 427 sources; worst color bias 51.73→37.82 DN16, with higher flat-field spatial RMS; positive-noise profiles bypass it |

In the earlier controlled comparison, V115 Small has4/4 known-camera scene means
above V114 Tiny and a slightly higher unseen mean, with3/5 scenes rising. V114
has slightly higher photo PSNR and lower color bias in that pair. Both improve
over V112. The newer V120 continuation supplies the measured general balance
above without applying a study-specific promotion threshold.

The [V114 eight-view pilot](v114-eight-view.md) is complete on the same24 saved
inputs as V112. Material gains average+.55750/.26416/.07938dB at ADC/ISO100/
ISO12800; both selected camera crops improve, with a small selected color-bias
tradeoff. Independent mean/metric checks and native review pass. This qualifies
a useful optional mode without claiming full427/all-camera/full-color-grid or
complete102MP results. The original V116 training/review chain is unchanged.

The [local material diagnosis](local-material-detail.md) finds substantial
remaining weak-detail attenuation: high-noise eight-view gain is.31813 in the
lowest contrast group, drawn only from feather/fur. Averaging slightly lowers
gain and residual error together. This complements the whole-patch scores and
does not change the general photo/color baseline choice.

## Run the current model

[Explicit selection](../configs/current-model.json):
`/mnt/external/demosaic/models/v120-final20000.pt`, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
The architecture retains V84's pretrained DRUNet RGB trunk, physical
noise/camera conditioning and official frozen DINOv3 ConvNeXt-Small pyramid.
[Inference and linear DNG/JPEG usage](usage.md).

The useful V117 photo-score option is
`/mnt/external/demosaic/models/v117-final20000.pt`, SHA256
`f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0`.
Its modest photo and weak-carrier gains coexist with lower camera means and
higher ADC bias. The current V120 recommendation keeps V117 available for its
higher photo mean and V114 for its lower tested ADC maximum.

The V114 Tiny alternative remains available at
`/mnt/external/demosaic/models/v114-final20000.pt`, SHA256
`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2`.
[Verified immutable endpoint aliases](results/v120-v121-endpoint-aliases-v1.json)
also preserve V121 for reproducible comparison. The
[selection change](results/current-model-v120-selection-v1.json) preserves the
previous selector and plot bytes. All five active plans pass their binding guards
before and after the change; their fixed V115 parents and inputs stay unchanged.

The [Q2/Sony/GFX50R gallery](cross-camera-qualitative.md) now compares both
current models with V104 and both released RawNIND variants on the same cached
inputs. Version differences are small in these six low-ISO regions; dark rocks
and window edges stay soft. Concrete texture looks finer than RawNIND, with no
clean reference establishing every fluctuation as real detail.

The [completed camera-linear development comparison](native-camera-development.md#v120v121-extension)
also includes V120/V121 on11 binned captures under added noise. V120 exceeds
RawNIND by3.69903dB in high-noise camera-RGB PSNR and retains substantially finer
native texture. V117 still has higher condition means; V121 changes only slightly.
Low-noise reference estimates and added-noise inputs do not establish broad
real high-ISO superiority.

V114 adds20k updates to the V112 EMA at seed63, using90,864 reviewed Commons
sources, native128/paired32 targets,4×→geometry→area2, zero optical PSFs,
weak textures and photographic contrast attenuation. Reconstruction epsilon
is.0003; paired RAW retains.0001. [Matched training](small-aligned-training.md).
V115 changes the official frozen encoder and eight fitted lateral initializers,
keeping the remaining V112 trunk/gate tensors and the matched training budget.
It is a fitted-transfer comparison, not capacity alone.

The [full saved-output local-detail comparison](local-material-detail.md#tiny-versus-fitted-small-on-the-same-full-photo-support)
now covers the same427 sources for both encoders. Weak natural-detail response
is nearly unchanged; Small's camera and eight-pixel advantages make it a useful
parent for the [V119 cleaned-data trial](cleaned-diverse-small-training.md), without suggesting that size alone fixes
faint detail. The [reviewed83-ID paired extension](paired-camera-sampling.md)
retains corrected reference masks and the original camera proportions. Both
discarded implementation checks passed and all20k training updates completed.
[V119's full review is complete](v119-quality.md): photo37.03831dB, a+.06131dB
gain over V115, but known/unseen54.10063/54.00742dB and ADC maximum2526.70DN16.
Weak high-noise photographic gain changes only.36422→.36523; no clear real
fine-mesh gain appears at matched conditioning. These camera/color regressions
favor retaining the useful choices above. The
[native-camera development comparison](native-camera-development.md) finds
much finer detail than RawNIND on its11 binned captures under added noise,
with V117 still slightly ahead of V119. This does not establish broad real
high-ISO superiority.

The [V120/V121 follow-up](paired32-weak-detail-training.md) keeps the V115 Small
architecture, tests corrected paired32 against V119's expansion, then tests the
reviewed90787-source/fourteen-region intervention at a matched20k budget.
Both original20k runs and independent numerical audits are complete. V120 keeps
V119's photo score with a+.21209dB known-camera recovery and much lower tested
ADC maximum. V121's small photo/known changes coexist with lower unseen mean
and a large ADC tail. [Two native exact-GT triplets per model](v120-v121-primary.md)
are published; full local statistics and selected native review are complete. Older Haar/new nominal
GFX conditioning is labeled; the additional fixed-Haar full-frame operators
now match older V115/V119 inputs exactly, with no clear large detail recovery.

## Quality and remaining work

The [completed V128 early-feature pilot](v128-feature-pilot-quality.md) finds no
useful gain against V126 after1,000 matched updates. Independent scoring and
all28 native boards, including both GFX pairs, are complete. The feature term
stays off by default. The [completed V129 curated27-region pilot](reviewed-detail-training-pilot.md)
also shows no useful visible recovery at1k, with+.00093dB ordinary/+.00042dB shadow
sRGB changes versus V126. All28 native boards are reviewed. The
[audited precision-gradient diagnostic](training-precision-gradients.md) led to
the [completed V130 matched FP32 trial](training-precision-pilot.md) against saved
V129 BF16. Ordinary/shadow sRGB changes are+0.00009/+0.00055dB; all28 native
boards show no clear large noisy-detail or real-mesh recovery. V120 remains the
general recommendation.

An optional [RAW spatial-attention branch](raw-spatial-features.md) now passes
genuine-V120 CPU/CUDA16+2 implementation checks. It adds22,664 parameters with
zero initial effect and a constant-preserving feature path. Model quality remains
unmeasured. The [V131/V132 trial](raw-spatial-training.md) has four exact-recipe
checks complete and20k production queued after V125's admission. Original mean-loss
inputs and the current V120 recommendation remain.

The completed48-call [faint ADC comparison](faint-adc-precision.md) shows V130's
slightly stronger gain and lower relative error in selected weak fur, grass and
wood strata against V129. Global faint-target sRGB PSNR falls0.01720dB and native
changes are subtle. Normal and fixed40× display comparisons are published.
The completed [V122/V123 frequency trial](v122-v123-quality.md) raises V123's
photo mean by0.05493dB against adapter-only V122, with lower unseen-camera mean
and ADC maximum4190.02DN16. Weak natural-detail gain changes only0.36465→0.36500;
both real GFX scenes remain soft. Full numerical/selected native review is complete.

The [independent-noise diagnostic](conditional-noise-response.md) separates
persistent error from output variance on four fixed targets. Faint fur/wood
remain biased after averaging independent V120/V117 restorations; strong bark
is mainly variance-limited. This supports testing a conditional-mean loss,
without an inference-strength or recommendation change. The multi-observation
mean is a diagnostic unavailable from one capture.
[V124/V125 now implement the matched training trial](conditional-mean-training.md)
on the cleaned90784/twenty-region data. V124's two-noise-view control is now
training; quality is unmeasured.

At2% contrast/ISO12800, Tiny's eight/sixteen-pixel carrier gains rise to
.13371/.71335; Small reaches.15217/.68865. Four-pixel structure remains nearly
absent. Native material/GFX examples show soft fine foliage and saturated signs,
and dark-camera mottling persists. The stronger released RawNIND reference
still wins four of nine camera scene means. Broad real-camera superiority
and state-of-the-art quality remain unproven. Separate ISO100/AHD RGB references
are not exact GT.

Both complete101.996MP outputs are verified. Ordered FP32 inference/blending
observations are116.57s for Tiny and101.66s for Small; differing warmup/workspace
states prevent a speed ranking. The100MP/10s target remains open. Hot-pixel
repair and [linear DNG/JPEG export](dng-export.md) are available; repair was off
in these comparisons. [Camera-outlier diagnostics](camera-outliers.md).

The [completed V116 data trial](v116-quality.md) holds Tiny's architecture fixed
while testing fine weak sources and reviewed reference masks. Eight-pixel weak
carrier gain rises from.13371 to.19123, but full-photo/unseen-CFA means fall
slightly, broad weak-material gain is unchanged and ADC worst bias rises to
239.15DN16. Native GFX foliage/neon softness remains. V114 retains the better
general balance; the new gains and weaknesses remain documented. Quality precedes speed.

The [completed V117/V118 loss pair](v117-v118-quality.md) starts directly from
V114 with matched20k budgets and common corrected data. V117's photo mean rises
to37.04408dB, with421/427 sources improving. V118's band term lowers weak natural
response against its control and worsens the ADC maximum to843.05DN16 despite a
small eight-pixel carrier gain. Complete metrics, native material/GFX comparisons
and RGB16 checks are published. Keep the term off for further quality work;
architecture and parent remain choices guided by their measured tradeoffs.

[PSNR history](performance-history.md) includes V120/V121 and earlier reviewed endpoints.
The [fixed V115/V117 output mean](fixed-tiny-small-mean.md) gives an intermediate
tradeoff: photo 37.02408dB and camera 54.31387/54.00195dB. It loses photo score
to V117 and camera means to V115, with unchanged visible GFX fine-detail loss.
This completed saved-output study does not establish a better trained architecture.
[Native review and publication checks](results/fixed-tiny-small-mean-review-v1.json).
Earlier useful comparisons retain their exact checkpoints and receipts:
[V112](v112-quality.md), [V104](v104-reviewed-corpus-quality.md),
[V102/V103](v102-v103-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
````

## Exact previous training-pipeline.md

SHA256: `184461ab51d73698c31d311b2dee7fd6a055c843e3266c2ed63e2a05b37ab5e1`.

````markdown
# Training data work, sampling order and batch size

Optional [per-source loss diagnostics](source-loss-diagnostics.md) trace
high-loss Commons examples to their actual source and crop without an additional
neural forward. They are disabled by default and enabled in V120–V123 recipes
and V124/V125; V119's frozen run is unchanged.

The [latest source inspection](v123-final-source-review.md) prepares a separate
90,781-source/29-region cohort, withholding one painted-tile-dominated frame
and adding actual weak petal veins and strong fine mesh. All27 preceding region
objects remain exact; actual reader checks cover all29. It has only discarded
[spatial-branch implementation checks](raw-spatial-features.md), with no production quality result.
The preceding90,782-source/27-region cohort stays fixed for the completed
[V129/V130 pilots](training-precision-pilot.md). The90,783-source/
[23-region option](v123-source-review-through9800.md) stays fixed for V126–V128.
The preceding
90,784-source/twenty-region snapshot remains frozen for
[V124/V125 independent-noise training](conditional-mean-training.md).
V122/V123 keep90,786/fourteen regions; V120/V121 retain their original inputs.
No sampling quota, blur policy or active/queued cohort changes from the latest
review. V124/V125 load16 unique targets once and draw32 simulated observations
after augmentation; real paired data stays16. This is a controlled quality
experiment, with no new throughput claim.

The [actual retained-target coverage check](training-target-contrast-coverage.md)
finds faint-band content in these training-check batches: 31.2% of eligible
ordinary-photo blocks and44.9% of reviewed-region blocks lie below5% contrast.
Native inspection also shows flat surfaces and soft backgrounds among high-count
crops. This bounded18-step prefix does not qualify a whole-corpus distribution
or justify replacing material inspection with a contrast-count admission rule.
All current and queued recipes remain fixed.

An optional [reviewed-material shadow exposure](reviewed-shadow-exposure.md)
is now implemented for a later trial. It uses one bounded scalar exposure,
preserving material geometry and current camera/noise draws, with old/default
preparation parity verified on CPU/CUDA. The new
[completed V126/V127 short pilot](reviewed-shadow-pilot-quality.md) tested it
from V120 with a shared.5 reviewed-region quota and found no useful gain.
Shadow exposure stays off by default and in the original V122/V123 and V124/V125 recipes.

The [completed V128 feature-loss pilot](v128-feature-pilot-quality.md) reuses completed V126
as its matched control on90,783 sources/23 regions. It adds a default-off spatial
loss through the shared frozen DINO first stage on Commons/native targets;
paired RAW and validation keep the existing loss. CPU/CUDA16+2 resume checks
pass with identical data/noise hashes. Its1,000-update pilot shows no useful gain.
Per-source traces retain base reconstruction loss while training logs separately
include the feature term. [V129 now tests the curated27-region cohort](reviewed-detail-training-pilot.md)
with feature/shadow terms off, preserving native/paired control input hashes.

The three requested changes are implemented and measured: geometry/PSF runs
between4× binning and the final2× reduction; only the selected domain is loaded;
and repeated throughput sweeps retain batch16. The matched geometry comparison
gains.50990dB over8×-then-geometry on all427 photos. On the actual RGB pipeline,
batch32 is only1.3% faster than16 while using roughly twice the CUDA allocation.
Details and limitations are recorded below.

The [completed V111/V112 quality trial](v112-quality.md) uses90,864 reviewed
sources. The [completed Tiny/Small continuations](v114-v115-quality.md)
establish V114 as a useful Tiny alternative; the newer
[V120 Small continuation](v120-v121-primary.md) is the current general recommendation.
This recipe retains native128/paired32,
zero optical PSFs, weak textures, photographic contrast attenuation and six
reviewed regions. The [Small rebase](small-aligned-training.md) reuses cached
training features/previews before a new V112-derived initializer and budget.
Earlier source pools,32-ROI comparisons and their receipts remain separately
recorded in the [source review](incoming-commons-quality.md) and
[V102/V103 study](v102-v103-quality-review.md).

The [completed V119 Small continuation](cleaned-diverse-small-training.md) uses
90,791 cleaned Commons sources and the corrected83-ID paired extension with
the original camera probabilities. Both16-step CPU/CUDA checks pass, including
all three data paths. Its [complete20k quality review](v119-quality.md) finds
a+.06131dB photo gain over V115, a−.22342dB known-camera change and a large ADC
color tail. The [V120/V121 follow-up](paired32-weak-detail-training.md) keeps
the Small architecture and restores corrected paired32; the second arm selects
reviewed90787/fourteen ROIs. All four discarded checks pass; V120 completed its
original20,000 updates, as has V121. Both independent numerical audits are complete. V120's
[early fine-mesh review](gfx-green-mesh.md#v120-after-correcting-the-paired-data-mix)
shows no clear recovery gain; saved/local and selected native review is complete, with main-GFX
profile differences [explicitly labeled](endpoint-quality-review.md#material-selection-and-gfx-conditioning). Both retain
zero optical PSFs, current geometry and batch16.

The completed [spectral](spectral-original4k-review.md) and
[late RGB](late-rgb-original4k-review.md) trials use native 256×256/B16 and all88,508
reviewed Commons training sources. Neither is promoted. The opt-in
[head-only training scope](late-rgb-head-only-engineering.md) protects the
mature common path and avoids its backward graph while learning refinement;
it retains the same geometry, selected-domain loading and controlled batch16.
Its [completed original4k review](late-rgb-head-only-original4k-review.md)
retains exact common tensors but fails quality promotion. It provides no new
training-throughput or data-expansion claim.

The default-off [input-context experiment](training-context-v86-v87.md)
separates prepared source size, actual forward size and central loss size.
`patch_size: 320`, `forward_patch_size` set to `256` or `320`,
`loss_patch_size: 256` and `validation_patch_size: 256` let both arms share
source/noise/target draws while only one sees the surrounding 32px border. RGB targets/masks and packed
RAW/variance/auxiliary fields retain their own coordinate units and Bayer
alignment; resume rejects changed geometry. Legacy recipes omit these options.
The [completed original4k comparison](training-context-original4k-review.md)
finds no positive matched photographic effect: +.00099dB with an interval
crossing zero, failed known-camera promotion and failed weak-detail gains.
Neither endpoint is promoted or extended; the default remains unchanged.

The [geometric source counts](results/training-context-original4k-publication-v1.json)
also constrain larger patches when preserving the final2× reduction:

| Native output size | Required4× cache short side | Existing train sources | Reviewed future sources |
| --- | --- | --- | --- |
| 256 | 512 | 84,867 | 88,508 |
| 320 | 640 | 50,912 | 54,059 |
| 384 | 768 | 21,709 | 23,674 |
| 512 | 1,024 | 1,305 | 1,679 |

The existing320 count matches the actual frozen cohort's source IDs exactly.
These are metadata-based geometric counts, without larger-patch performance or
throughput claims. Native256 retains the full reviewed source population for
the next experiment; the full future corpus is not qualified for320.

The mixed trainer previously prepared a Commons batch on **every** optimizer
step, including steps that replaced it with paired RAW or native-RAW synthetic
data. Domain selection now precedes loading. Each loader samples only its
selected global steps, starts workers on first use, and stops prefetch at the
requested training endpoint. This removes discarded Commons augmentation while
preserving original sample indices, domain decisions and physical noise draws.

The three requested changes have now been measured: augmentation runs between
the 4× and final 2× reductions, selected-domain loading removes discarded Commons
batches, and batch16 remains the controlled setting after repeat throughput
sweeps. The matched [augmentation quality comparison](geometry-corpus-v34-v36-review.md)
improved full427-photo PSNR by .50990dB versus8×-then-geometry, with unchanged
validation targets. The [RGB-pipeline sweep](current-pipeline-batch-sweep.md)
found batch 32 only 1.3% faster than 16 while using roughly twice the CUDA allocation;
the [later RAW-head sweep](raw-kernel-training-batch-sweep.md) also retained 16.

An [opt-in deterministic execution policy](training-execution.md) now passes
two fresh six-update CUDA replays across all three domains, including exact
model/EMA/optimizer/RNG states. The throughput policy remains the default;
execution settings and dataset additions need their own controlled measurements.

A separate [normalization study and opt-in training augmentation](normalization-augmentation.md)
addresses sensitivity to the region used for neural feature coordinates. It
keeps RAW/targets fixed and leaves the geometry order intact. Its
[completed original4k GPU review](normalization-v68-v69-original4k-review.md)
found a small matched photo gain; texture/color limitations prevented promotion.
The [experimental RAW-native backbone](packed-isotropic.md) retains the same
geometry and selected-domain loading. Its completed sweep selects batch4 for
that architecture; the older RGB model retains batch16. The later
[mixed optimizer-batch comparison](mixed-optimizer-batches.md) finds four B4
source groups faster than a joined B16 for the RAW-native model. Its
[completed160k-example quality review](packed-isotropic-mixed16-quarter-review.md)
finds gains over its own parents but losses against older equal-example models.
Neither new arm is promoted or automatically extended. These model comparisons
change additional training factors and do not establish a batch-only quality gain.

For seed45's first 1,000 steps, 514 select Commons/procedural, 230 paired RAW and
256 native-RAW synthetic. Batch4 formerly consumed 4,000 Commons examples
(plus possible unused prefetched work);
the new route prepares 2,056. **All 41 logged V30 observation/target fingerprints
were reproduced exactly** with selected-only loading. Unlogged observations were
not separately hashed. Mixed-domain interruption/restart tests retain identical
weights and EMA, and guards reject any fetch from an unselected domain.

## Internal training artifacts

The optional [paired camera sampler](paired-camera-sampling.md) lets the reviewed
83-ID extension retain the original32-group camera proportions. A separate
manifest preserves the four corrected legacy masks and every admitted new case.
Default scene sampling stays exact; changing camera probabilities on resume is
rejected. The93 focused sampling/admission/resume checks and actual76-sample
native256 reader preflight pass without production neural work.

The [completed V117/V118 loss pair](v117-v118-quality.md) retains native256/B16
and the current90,864-source geometry. Metadata coverage at4×→area2 is90,864
sources for256px,55,998 for320px,24,753 for384px and1,762 for512px, without
upscaling. A global larger-patch trial would also change source coverage.

The recipe preparer now accepts artifacts inside its own frozen `root/work/`
workspace. Internal jobs declare128/96GiB internal phase/runtime headroom and
208GiB external input reserves; existing external jobs retain their32/16GiB
internal and256/128GiB external limits. Six path/resource tests pass. The new
pair also verifies zero band evaluations for the default-off control and paired
RAW, and reuses existing production trace hashes to avoid duplicate hashing.
All original executed sources and receipts keep their bytes.

## Augmentation before the final reduction

The optional `augmentation_downsample: 2` training path is:

1. Decode original Commons images with their ICC profile, convert to linear
   sRGB, and average 4×4 source cells into a uint16 cache.
2. Crop at twice the target resolution. Apply exact quarter-turns/flips.
3. When projective augmentation is drawn, combine crop-to-output scaling and
   projective rotation/shear in one resampling operation at twice the target
   resolution. Otherwise use area scaling at that resolution.
4. Apply sampled optical PSFs in final-pixel units at the higher resolution.
5. Average 2×2 linear cells to the final patch; then apply camera/exposure,
   Bayer masking, Poisson/read noise and ADC simulation.

There is no geometric interpolation after the last reduction. Synthetic detail
and smooth fields also use the higher intermediate resolution in this mode.
Interpolation error is reduced in a controlled test; it is not eliminated.
For one continuous cosine/projective fixture, MSE against a denser integration
reference falls from .00493965 to .00047290. This single sampling experiment is
not evidence of trained-model quality or universal improvement.

The loader requires metadata declaring 4×-binned caches, and outputs native
256px patches as FP32. Four actual source checks found at most one uint16 code
of difference between unaugmented 4×→2× reduction and the old direct 8× cache.
Source files and frozen manifests remain unchanged. Existing configurations
default to the original path, preserving ongoing experiments.

Prepare the same source selection at 4× without changing held-out membership:

```bash
source scripts/env.sh
uv run --no-sync demosaic prepare --source /mnt/external/qi \
  --output /mnt/external/demosaic/commons-frozen44732-bin4-v1 \
  --factor 4 --min-size 512 --workers 2 \
  --selection-manifest /mnt/external/demosaic/audits/commons-44732-v1/manifest.jsonl
```

Both complete frozen 4× corpora are prepared and checked: 40,170 and 41,978
training sources, with unchanged 2,303 validation and 2,255 test sources.
Preparation followed the batch sweep and full-frame review to avoid competing
with throughput measurements. Excluded sources remain excluded; only
training rows enter the training loader. Use `manifest` for the new 4× training
selection and explicitly retain the original 8× audited `validation_manifest`
in a new experiment configuration. Validation source hashes and source snapshots
are recorded, and resume rejects a changed validation/augmentation recipe.
Newly downloaded images are not silently admitted by this frozen rebinning job.

The option also applies to [native camera-linear targets](native-raw-targets.md#augmentation-before-the-final-reduction)
via `raw_clean_augmentation_downsample: 2`. Their4× cache is complete with the
same53 training captures/31 scenes. Registered paired RAW uses exact sensor-phase
transforms. Existing experiments retain their original8× configurations.

`scripts/freeze_rebinned_manifest.py` freezes the complete Commons4× producer
output only after its lock is released and all active source identities/splits
match the audited selection exactly. Partial output, changed protected splits,
missing sources and an existing frozen manifest are rejected. A waiting owned
job created `/mnt/external/demosaic/audits/commons-bin4-frozen44732-v1/manifest.jsonl`
after full preparation. [V34's matched augmentation recipe](../configs/dino-anchored-pre-downsample-b16-v34.yaml)
points there, with original8× validation; it cannot accidentally train on the
producer's earlier 256-source partial manifest. V34 and V36 have completed their
first 1,000-update and full-photo reviews.

For general ingestion while the archive downloads, SQLite now reads committed
WAL data in read-only mode and releases its metadata snapshot before decoding.
The old immutable connection could miss newly committed downloads. Frozen
selection rebinning reads its supplied manifest instead of the changing index.

## Reviewed photographic regions

The opt-in reader accepts an exact manifest-bound photographic catalogue.
Current V119 uses the original six regions rebound to its 90,791-source cohort.
An optional [14-region material catalogue](../configs/low-contrast-training-rois-cleaned90787-v1.json)
preserves those six and adds eight measured low-contrast contexts for the
90,787-source future cohort. All fourteen pass actual native256 reader checks;
the bank is untrained and unapplied. [Native examples, selection and limits](weak-photographic-targets.md).
The earlier [32-region catalogue](../configs/low-contrast-training-rois-curated-v3.json)
retains its exact 88,477-source binding and completed six-versus32 comparison.
`reviewed_roi_catalogue` names the chosen catalogue; `reviewed_roi_fraction` defaults to
`0.0` and gives the selection probability **conditional on a photographic
Commons sample**. Flat and synthetic samples retain their existing shares.
Completed V101 used the [original six-region catalogue](../configs/low-contrast-training-rois-v1.json)
at `.05`; V100 left it disabled. Their [current selected-detail results](heldout-detail.md)
and the [full matched results](v84-curated-quality-review.md) are available. The expanded catalogue
was used by V103 with its matching manifest; V102 used the same original six
regions rebound to that manifest. Their completed comparison found a tiny mixed
effect, so expanding the catalogue at an unchanged quota is not an established
quality improvement.

Selection happens before opening the image cache. A selected sample loads only
its reviewed source, crops within the recorded 512×512 bin4 region, applies the
existing geometry, then performs the final area2 reduction. Native256 uses the
whole recorded context before augmentation; smaller patches stay within it.
This requires the training split, `augmentation_downsample: 2` and a prepared
patch no larger than256. It changes source and field-of-view sampling, so a
future comparison must account for both effects. Blur, contrast attenuation,
noise and domain scheduling retain their separately configured policies.

The reader checks exact training membership, manifest and cache hashes, aligned
ROI bounds, dtype/shape, and recorded crop/target hashes. The trainer snapshots
the catalogue bytes and SHA256; resume rejects a changed catalogue or fraction.
`CleanDataset.reviewed_roi_for_index(index)` exposes the deterministic choice
for data audits. The catalogue's area2 target hash identifies its reviewed
unaugmented view; it does not identify every augmented training tensor.

The [CPU readiness receipt](results/reviewed-ROI-loader-CPU-readiness-v1.json)
records141 passing focused checks, including actual tiny CPU training with
exact interrupted/resumed model, EMA and optimizer state. A separate clean-data
probe checked224 real samples from the first24 scheduled steps: all224 disabled
outputs matched the archived V95 reader, and all162 untreated active outputs
remained bit-exact. It selected62 ROI samples covering all six sources, loaded
one cache per photograph, and matched six tensors across two spawned workers.
That probe used fraction0.5 solely to exercise the reader. It ran no denoising
model, optimizer or sensor-noise simulation. These are implementation checks;
V101 now has trained evidence for its complete recipe package; the ROI-only
effect is not isolated. The expanded 32-source catalogue has reader/data proof,
and the [completed V102/V103 comparison](v102-v103-quality-review.md) shows
a tiny mixed ROI effect. V102 final20k also shows
[selected-detail progress](heldout-detail.md) using the original six regions;
it does not measure the expanded32-region effect.

## Current recipe sampling and targets

The V101 recipe keeps `.20` total synthetic and `.10` flat shares within the
Commons domain. `weak_texture_fraction: .15` takes 15 percentage points from
that synthetic total; it is roughly 75% of synthetic Commons samples, not 15%
of that component. Photographic contrast attenuation has probability `.25`
conditional on a photographic sample. Reviewed-region sampling has its own
conditional probability `.05`.

Reconstructing the exact seed59 full10,000-update/B16 schedule gives:

| Source type | Scheduled examples | Share of all examples |
| --- | ---: | ---: |
| Photographic Commons, including reviewed regions | 55,843 | 34.902% |
| Weak synthetic | 11,970 | 7.481% |
| Other synthetic | 4,106 | 2.566% |
| Flat fields | 8,049 | 5.031% |
| Native RAW synthetic | 40,512 | 25.320% |
| Registered paired RAW | 39,520 | 24.700% |

The schedule selects 4,998 Commons, 2,532 native and 2,470 paired steps.
Within the photographic Commons row, 2,844 examples use reviewed regions:
5.093% of those photographs and 1.778% of all160,000 examples. Each of the six
reviewed sources is scheduled443–517 times. These are deterministic schedule
counts for the completed V101 schedule, not the new V102/V103 runs.
The [full source-coverage audit](results/training-v100-v101-source-coverage-v1.json)
reconciles these counts with the finished endpoints.

Actual clean-target reconstruction at each source's earliest scheduled index
confirms finite FP32 native256 tensors and zero optical-PSF calls in those
six reads. One draw applies linear contrast attenuation with scale `.191659`;
the other five do not. The reader mixes toward the patch's per-channel mean,
preserving geometry while reducing contrast. The captured before/after pair
matches that affine operation within2e-7 in linear units.

![Native clean training inputs: lichen before/after attenuation and unchanged fishing-net target](images/training-v101-targets-native.png)

Each panel is an unchanged160×160 crop at [48,48,160,160] inside its augmented
256-pixel target, with shared ×1 exposure and linear-sRGB→sRGB display.
These are clean training-data illustrations, without sensor noise or a neural
prediction. They do not establish improved trained detail retention.
[Source/ROI/sample-index/display metadata](images/training-v101-targets-native.json) ·
[Counts, frozen reader references and actual viewing](results/training-v101-sampling-and-targets-v1.json).
All six reconstructed contexts were inspected through12 native before/after
cells; the illustration repeats four of those cells without resizing.

Sources: [GT1976, pale beard lichen](https://commons.wikimedia.org/wiki/File:2017-07-20_%28153%29_Unidentified_Usnea_%28beard_lichen%29_at_Zedlacher_Paradies,_Matrei_in_Osttirol,_Austria.jpg)
and [Basile Morin, fishing net](https://commons.wikimedia.org/wiki/File:Sitting_boy_weaving_a_fishing_net_in_Laos.jpg),
[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0), modified through
binning, cropping, training geometry and the indicated contrast attenuation.

## Batch-size sweep

The current joint RAW-kernel model has its own
[completed batch sweep](raw-kernel-training-batch-sweep.md): B4/B8/B16 average
14.62/15.72/15.81patches/s including selected-domain loading and augmentation.
B16 is only.56% above B8. B32/48/64 are memory skips, not measurements. The
production model/data/schedule/LR remain unchanged; all timing updates are discarded.
The earlier RGB-model measurements below do not settle its batch choice.

`scripts/benchmark_training.py` runs fresh processes for batches 4/8/16/32/64,
two repeats in a deterministic shuffled order, using the same initializer,
model, frozen manifests, mixed-domain schedule, LR and data-worker counts.
It excludes 15 warmup steps and measures 45 steps per case. Timing includes
actual selected-domain I/O/augmentation, physical degradation/GAT conditioning,
frozen DINO features, forward/backward, AdamW and EMA. It excludes validation,
startup and checkpoint serialization. All cases must share the same source hash.

```bash
source scripts/env.sh
uv run --no-sync python scripts/benchmark_training.py \
  configs/dino-anchored-stabilized-rgb-v30.yaml \
  --initialize /mnt/external/demosaic/runs/dino-anchored-stabilized-rgb-v30/initialization-v30.pt \
  --output /mnt/external/demosaic/benchmarks/mixed-training-batch-sweep-v1
```

The completed sweep used the existing 8× data path so only batch size varies.
Larger batches change samples per optimizer update and are not a convergence
comparison. A new batch size must be evaluated for image quality; throughput
alone does not justify scaling LR or claiming a better model. The 4×→2× path
also needs its own throughput check before choosing its production settings.

| Batch | Mean images/s | Two-run range | Peak CUDA GB |
| ---: | ---: | ---: | ---: |
| 4 | 22.52 | 22.40–22.64 | 2.23 |
| 8 | 24.56 | 24.38–24.74 | 3.72 |
| **16** | **26.14** | **25.19–27.09** | **6.94** |
| 32 | 26.42 | 25.67–27.18 | 13.39 |
| 64 | 26.27 | 25.53–27.01 | 26.28 |

Choose **batch16** for the next quality trial: approximately16% more images/s
than batch4, within1.1% of batch32's mean, with about half its CUDA allocation.
The largest batch provides no measured benefit here. Ranges reflect two shared
machine runs, not confidence intervals; no claim of a unique hardware optimum.
Keep LR unchanged and review image quality before extending training. Peak CUDA
allocation is not total system RAM usage. All10 cases share the same archived
source hash. [Complete measurements and reproduction receipt](results/training-batch-sweep-v1.json).

The [second sweep](current-pipeline-batch-sweep.md) is complete on the actual
4× Commons/native128 pipeline, using V43's frozen first1000 EMA initializer.
It repeats batches 4/8/16/32/64 twice with 15 excluded warmup and 45 measured
updates. Batch16 reaches **30.81 native 256×256px patches/s**, 12.1% above batch4.
Batch32 is only 1.3% faster, using 13.41 GB versus 6.95 GB peak CUDA allocation.
Batch64 adds no clear benefit. Keep batch16 fixed in controlled quality trials.
All ten cases verify the same initializer, source and data/augmentation recipe.
The owned corpus evaluation finished and exited before this sweep started.
[Complete measurements](results/training-batch-sweep-v2.json).

[V31's recipe](../configs/dino-anchored-stabilized-rgb-b16-v31.yaml) continues
frozen V30 step1000 with batch16, retaining model/AdamW/EMA/RNG state and the
existing8× dataset. It stops after1,000 additional updates (step 2000) for paired,
synthetic and GFX review. This processes16,000 additional examples and changes
global sample indices to the batch16 recipe. It is not an equal-image or
batch-only quality ablation. The complete4× selection prepares separately;
current training does not silently switch to its partial output.

A genuine DINO BF16 backward smoke on the actual 4×→2× Commons batch also passed:
finite FP32 output and nonzero measurement-adapter gradients. This verifies
execution, not the quality of a model trained with the new augmentation path.

Validation: **248 tests passed in 20.53s**, including sampling precision,
projective/constant-color behavior, frozen source splits, live WAL ingestion,
selected-domain fetch guards, and deterministic mixed-data restart. Ruff passed.

Subsequent [invariant-grid caching](expectation-grid-performance.md) removes
repeated Poisson table work without changing numeric outputs. The
[V31 quality review](anchored-rgb-b16-v31-review.md) finds synthetic gains but
real-camera regression after batch16 continuation, so V30 remains the quality
reference. Lower-LR/data-mixture trials are separate from the throughput choice.

The subsequent invariant-grid comparison reaches29.07images/s versus26.18
with the original table construction at batch16 (two alternating runs each,
same6.94GB allocation). Full validation including the native4 extension and
complete-manifest freeze gate now passes **256 tests**. Model quality remains
under development; these software/throughput checks do not establish it.

The completed [V32/V33 lower-LR mixture review](low-lr-paired-v32-v33-review.md)
uses batch16 and the cached grid with the original8× data. V32 improves full427
photo PSNR by.17289dB over V30; V33 improves real rendered means while giving up
unseen measured-CFA accuracy versus V30. V33 continues only to its next review
gate. The [first Commons extension](results/commons-extension-20261016-v1.json)
adds1,808 eligible training sources in a separate frozen manifest. Neither this
extension nor partial4× preparation has been admitted to these matched trials.
The new ingestion/audit tests bring the full suite to **260 passing tests**.

## Matched corpus and augmentation pilot

These four recipes share the V30 step1000 EMA initializer, fresh AdamW/EMA,
batch 16, seed 46, LR 3e-5 / planned 3,000 steps and a first review after 1,000
updates. Domain proportions stay 25% paired / 25% native / 50% Commons, with
the same paired/native source identities. Every arm validates on the original
frozen 8× manifest. This is a single-seed pilot, not convergence evidence.

| Commons train corpus | Existing 8× augmentation | 4× → geometry/PSF → 2× |
| --- | --- | --- |
| 40,170 sources | V32: first1k/2k reviewed, stopped | [V34](../configs/dino-anchored-pre-downsample-b16-v34.yaml): first1k/full427 reviewed |
| 41,978 sources | [V35](../configs/dino-anchored-expanded-b16-v35.yaml): first1k/2k reviewed, stopped | [V36](../configs/dino-anchored-expanded-pre-downsample-b16-v36.yaml): first1k/full427 reviewed |

The geometry change applies to both Commons and native synthetic targets;
registered paired RAW keeps its exact sensor-phase transforms. The corpus change
adds only the [1,808 audited Commons training sources](results/commons-extension-20261016-v1.json).
V35's validation, paired and native manifest hashes and runtime code/initializer
match V32. All 27 shared logged paired/native batches match at the first 1k gate;
Commons draws change with the corpus.
V34/V36 started only after their complete frozen 4× manifests existed. The expanded
4× job prepares only new sources and reuses old cache paths, preserving protected
membership and attribution.

[V35's first review](expanded-v35-1k-review.md) finds +.04306 dB unseen primary
PSNR versus V32 (95% scene interval[+.00727,+.07886]) and −.06106 dB on the
16-photo synthetic screen. No decisive GFX visual gain is established. Both
have now completed [the matched step2000 gate](corpus-v32-v35-2k-review.md) and
stopped. At2k the expanded arm improves known means but trails V32 on unseen
means; its own unseen primary mean falls .10983dB versus its first1k. All51
logged paired/native hashes match across82 observations per arm. Full427 and
full102MP checks are complete. The [gain diagnostic](paired-bias-v35.md)
does not support adding an input-only gain correction to this model.
[Startup/runtime identities and rebin implementation](results/commons-augmentation-pilot-startup.json)
are retained; V35's report records its frozen first 1k weights separately.

[V33's step 2000 continuation review](paired50-v33-2k-review.md) is complete and
stopped: better unseen primary PSNR versus its first 1k, mixed rendered scores,
and a lower photographic screen mean. It does not replace these matched controls.
The rebin/merge guards bring validation to **271 passing tests**.

The [preparation worker sweep](results/commons4-preparation-workers-v1.json) selects
eight workers for the remaining base4× preparation, reusing26,314 finished
caches. New-source4× preparation is complete (1,808 train, no failures). Its
merge completed after the full base audit. The detached V34/V36 workflow waited
for the preceding full quality review to finish before either trainer started,
checks exact original source memberships and source-module bytes, and retains
the same initializer/schedule. The source bundle hash also includes the native
manifest, so the4× versus8× hashes intentionally differ in that data file;
code files, validation and paired sources must match exactly. Logged paired
draws must match V32; native draws must match between V34/V36. Public RAW
candidates remain outside these recipes. Current validation passes **279 tests**.


Both [complete4× corpora](results/commons-four-complete.json) are now frozen,
with40,170/41,978 training sources and unchanged2,303/2,255 validation/test
membership. V34 started on2026-10-16 at02:53:56UTC; V36 followed sequentially.
The preflight verified source-module bytes and the initializer against V32;
all12 logged paired batches through step625 match. The new source-bundle SHA is
`15af15b4c3e817599e54d1e3995dbd95f9f14213dace0e3a7735985cef8300ea`;
its native4× manifest is the intended data-file difference from the8× control.
The full V32/V35 review is also complete: V32-2k gains.06767dB over its first1k
on all427 photos, while the expanded arm trails it by.12055dB. Full-frame
RGB16/ICC outputs and both RawNIND calibrations are verified. Small screens did
not predict the continuation gains; use the [full report](corpus-v32-v35-2k-review.md).


The [completed augmentation review](geometry-corpus-v34-v36-review.md) confirms
V34's **+0.50990 dB** full-photo gain over V32 at the matched first 1,000 updates,
95% source interval [+0.47646,+0.54728]. The expanded arm gains +0.63571 dB over
its own old-order control. V36 differs from V34 by only +0.00916 dB, with an
interval crossing zero and weaker procedural/unseen means. V34's real-camera
primary changes are small and uncertain. The new order becomes the next trial's
training recipe; its original 8× scoring protocol remains fixed. All 16 logged
paired hashes match across V32/V34/V36, and all 11 logged native hashes match
between the two 4× arms. Both stop at the review gate. Fine texture is still
too soft; the full-frame GFX review is documented with the same fixed regions.

The subsequent [packed detail review](packed-detail-v40-v41-review.md) uses this
same geometry, batch 16 and selected-domain loading. Its physical detail prior
recovers much of the first packed model's real-camera noise loss, but remains
below the full-resolution control. A 10× phase-head LR does not close the gap.
All 41 logged V38/V40/V41 observation hashes match, and the full 427-photo and
102 MP GFX checks are complete. The final source passes 321 tests; the stronger
augmentation order remains adopted independently of these architecture trials.
````
