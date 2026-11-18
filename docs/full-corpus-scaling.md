# Full-corpus scaling and whole-scene context training

**The 20k control is complete and the 100k run has completed five ordinary-photo passes.**
The [20k review](full-corpus-control20k-review.md) verifies all320,000 target slots,
all90,778 photo IDs and the first full ordinary epoch at17,039. Faint fidelity
recovers0.59370 dB from10k, remaining0.02061 dB below V120; ordinary/shadow means
improve slightly. Both protected fence families still lack convincing new fine
crossings. V120 remains recommended. The [full endpoint benchmark](full-corpus-primary-admission.md)
is running, with subsequent broader weak-band analysis queued. The
[complete camera panels](full-corpus-control20k-camera-review.md) gain0.03285 dB
known/lose0.04067 unseen. The [complete color panel](full-corpus-control20k-color-review.md)
finds worst ADC bias765.7 DN16 versus V12055.5,largely repaired by physical
Malvar/bin correction. Standard broad photo results remain pending. The separate
[427-photo faint ADC suite](full427-faint-adc.md) is complete. Projection lowers
the weakest-band Corpus20k error from 2.594 to 1.901 DN16, essentially matching
projected V120. The protocol uses original-source masks and four-CFA,
equal-source pooling.

The [three-way 20k checkpoint review](full-corpus-long20k-native.md)
is now complete. The long schedule lowers faint fine-band error for
three of four materials and loses 0.19124 dB mean faint sRGB PSNR versus
the short schedule. Both standing GFX families were reviewed.

The latest [long-schedule 86k review](full-corpus-long86k-native.md)
gains 0.569 dB faint ADC sRGB over V120 on the retained material panel.
Fine-band error improves on bark, fur and wood. Worst ADC flat bias
on the two-color spot check falls from 1,489.97 DN16 at 50k to 20.58
at 86k, with V120 at 15.08. The [broader ADC follow-up](full-corpus-long86k-adc.md)
finds higher raw 86k weakest-band error across 64 faint photographs and
a 1,429.92 DN16 raw bias on the full flat-color grid. Bin Malvar reduces
both errors below matched projected V120. Both GFX scenes still lack
convincing new fine crossings.

The 100k endpoint observer is running. It verified the 110 native
inputs and all 220 saved V120/86k predictions. Once the training
controller records successful completion, it checks the retained
checkpoint and starts the native comparison and fixed 3,162-case CPU
benchmark. The primary comparison uses the existing, matched V120
predictions. The adoption path reproduced the existing 54 camera
batches in a dry run. Endpoint scores and native inspection are pending.
[Bound review queue and preflight receipts](results/full-corpus-long100k-review-queue-v1/publication.json).

All three whole-scene comparison arms are trained. Their [native review](whole-scene-context-native-review.md),
[64-source study](whole-scene-context-development64.md) and
[camera review](whole-scene-context-camera-review.md) find small quiet/partial
unseen-camera gains with mixed detail/color costs; their full427 collection runs
separately. [Checkpoint recovery](full-corpus-checkpoint-cpu-recovery.md)
preserves both failures, exact replay and the completed20k state. The long arm
continues from its original1k Adam/EMA/RNG state and100k horizon.
This implements the [training-scale review](training-scale-pipeline-review-2026-11-17.md)
and complements the [scene-context experiment](whole-scene-context-next-test.md).
The separate [expanded scene corpus](expanded-scene-corpus.md) qualifies 90,692
photos for future matched whole-scene training.

[Exact admission, profiles, source snapshots and launch receipts](results/full-corpus-training-setup-v1/publication.json) ·
[Independent saved-state/source audit](results/full-corpus-training-setup-v1/independent-review.json) ·
[Scene model/data qualification](results/whole-scene-context-training-setup-v1/publication.json).

## Larger coverage with the existing full model

Both scaling arms start freshly from the same V120 Small EMA, with the same
pretrained DRUNet, frozen official DINOv3 ConvNeXt-Small, physical precision,
loss and bin4 → geometry → area2 targets. The cleaned90,778-photo/33-region
cohort uses the existing verified shuffled photographic-epoch reader. Reviewed
ROIs receive5% of photographic draws. Public native-RAW and paired-RAW domains
retain25% each; the Commons domain retains its genuinely flat/procedural/weak
examples. Actual catalogue sizes are106 native training fields and32 paired
training scenes;128 describes the native catalogue including22 validation fields.
Protected private GFX media/JPEGs/siblings remain outside all training.

This addresses under-coverage of the available corpus. The previous V131/V132
20k schedule visited42,086 of90,781 photo IDs, with half its photographic draws
concentrated on29 reviewed sources. Those figures describe that continuation,
not lifetime exposure through the parent or backbone. More source visits, crop
locations and corruption draws are useful dimensions to test separately.

|Declared schedule|20k control|100k continuation|
|---|---:|---:|
|Total target slots, B16|320,000|1,600,000|
|Ordinary photographic draws|106,823|531,903|
|Reviewed photographic draws|5,601|27,905|
|Commons procedural/flat draws|48,312|239,712|
|Ordinary photo IDs covered|90,778|90,778|
|Complete ordinary-photo epochs|1|5|
|Partial next epoch|16,045|78,013|

The20k column is now independently confirmed by actual execution. The100k
column remains a planned full-horizon order; its continuation is running.
Source-order totals do not establish quality or lifetime novelty.
The first complete ordinary-photo epoch occurs at step17,039. The first320k
source slots of the two orders match exactly. In the100k ordinary sequence,
12,765 sources have five visits and78,013 have six; reviewed visits are additional.
The schedule is generated once, not restarted at each milestone. Repeated visits
use fresh global sample indices, spatial augmentation, camera/exposure and
per-step sensor RNG. Correlated/overlapping crops are not counted as disjoint
native detail or newly independent scene layouts.

### Completed20k: actual execution

The [completed source/state audit](results/full-corpus-control20k-review-v1/completed-training-audit.json)
combines original1–6k, valid6,001–13k and replayed13,001–20k. It excludes the
abandoned13,001–14k segment. All20,000 step/global indices,320,000 target slots
and80 conditioning chunks are checked. Actual112,424 photo visits comprise
106,823 ordinary/5,601 reviewed draws; all90,778 ordinary IDs are present,
74,733 once/16,045 twice. The first epoch completes at17,039. All1,000 replayed
source rows/four conditioning chunks exactly match the abandoned segment.

The complete20k raw/EMA/Adam/RNG checkpoint is
`633053370bdfb455d738ce0e3af686cb61e8dcac7c501954eb3b2293738a3795`.
Domain batches:10,046 Commons/4,965 native/4,989 paired. Native/paired actual
distinct IDs remain unrecorded. Reported retained-loop windows total12,490.150s;
attempted controller phases total20,104.376s including stalls/replay/concurrency.
Training completion, targeted numerical/native completion and pending broad
scores are distinguished in the [endpoint report](full-corpus-control20k-review.md).

### Long-schedule 20k milestone

The 100k run has saved update 20,000, with an intact raw/EMA/Adam/RNG state
and its original cosine horizon. This is its first equal-budget checkpoint
against the separately annealed control. The saved checkpoint SHA256 is
`a4e64a3b553e5e70683850bc93e6a99f1ad020d7b2c663936bad8098d604bf70`.
All 90,778 ordinary training sources were visited by update 17,039. Across
320,000 target slots, both schedules recorded the same 106,823 ordinary
visits, 5,601 reviewed visits, crop choices and data seeds. All 80
conditioning chunks and saved Python, CPU and CUDA RNG states match. The
order-header hashes differ, as declared. Of 91 raw and 91 EMA tensors,
89 in each group differ between the two states. Native and paired RAW
source IDs are unlogged, and the audit covers the recorded inputs.
[Milestone state, independent audit and launch](results/full-corpus-long20k-progress-v1/publication.json) ·
[First-epoch audit](results/scene-wave-guides-v1/long100k-first-epoch.json).

The recorded training loops take 695.68 seconds for updates 1–1,000 and
12,432.29 seconds for updates 1,001–20,000. These windows exclude the pause
between phases and the final checkpoint write. The separate CPU image
review has its own timing. [Training timing and exact log prefix](results/full-corpus-long20k-progress-v1/timing-and-audit-followup.json).

All 110 retained inputs ran through fresh V120, the completed 20k control
and the long-schedule 20k EMA. All 220 control predictions match the
earlier review bit for bit. The audit and both GFX families are covered
in the [completed native review](full-corpus-long20k-native.md).

### Long-schedule 50k milestone

The trainer saved the immutable 50k state and continued on the same
100k horizon. Checkpoint SHA256 is
`1560138b11371f58f2df33c52f026f9bd941aa1e5f336c607cefcd0c0a04d431`.
The checkpoint has 91 raw and 91 EMA tensors, 89 Adam states at step
50,000, and Python, Torch CPU and CUDA RNG. The retained resumed loop
elapsed time at the 50,000 training log is 33,736.87 seconds for updates
1,001–50,000, in addition to the 695.68-second initial loop. The final
validation and checkpoint write follow that observation. Native evaluation
has a separate timing and reuses the 220 verified V120/long-20k controls.
[Checkpoint and launch audit](results/full-corpus-long50k-prefix-v1/checkpoint-verified.json).

The [completed 110-input review](full-corpus-long50k-native.md) finds
small ordinary/shadow gains, weaker fine-band fidelity on all four faint
materials than V120, and severe orange ADC color error in two Bayer
layouts. Both standing GFX scenes were inspected. V120 remains recommended.

The prefix contains 800,000 target slots and 266,909 ordinary photo
draws, with 85,353 sources seen three times and 5,425 seen twice. It
also records 14,002 reviewed-region draws from 33 sources. Across sources
with a third visit, the median original cache field seen in the union
of crop rectangles grows from **54.4%** after one visit to **69.1%**
after two and **76.7%** after three. Median additional coverage from the
third visit is 5.0% of the source field. There are 5,346 third crops
fully within the earlier union. Those samples still have fresh geometric
augmentation and sensor corruption. The rectangles describe coverage
before augmentation. [Source, conditioning and crop audit](results/full-corpus-long50k-prefix-v1/source-and-crop-audit.json).

### Third photographic epoch and the 58k prefix

The executed source ledger completes the third ordinary-photo epoch at
update **51,009**. By update 58,000, the run has processed **928,000**
target slots, including 309,471 ordinary photo draws. All 90,778 photos
appear at least three times and 37,137 appear four times. The median
fourth crop adds **2.38%** of its source's cached area to the union of
earlier crops. The cumulative median for this subset is **81.21%**.
For 4,138 fourth visits, the new rectangle falls entirely within the
previous union. The coverage measurement uses pre-augmentation rectangles
and the audited draw seeds advance throughout the run.

The prefix audit matches every recorded ordinary identity and every
update seed to the fixed schedule, verifies the original 50k log prefix
and checks 32 additional conditioning chunks. The latest image-quality
evaluation is the retained 50k checkpoint.
[58k source audit](results/full-corpus-long58k-prefix-v1/source-audit.json) ·
[Audit code](results/full-corpus-long58k-prefix-v1/audit.py.gz).

### Fourth photographic epoch and the 72k prefix

The source ledger completes the fourth ordinary-photo epoch at
update **68,269**. Through update 72,000 it records **1,152,000** target
slots and **383,272** ordinary photo draws. All **90,778** ordinary
photos appear at least four times, and 20,160 appear for a fifth visit.
The median fifth crop adds **1.26%** of the cached image to the union of
the prior four rectangles. This subset reaches **84.01%** median total
coverage. The fifth crop is fully within the prior union for 3,202
images. These are cached rectangles before geometric augmentation.

The audit binds the published 58k prefix, verifies source order and
draw seeds, and checks 56 additional saved conditioning chunks.
[72k source audit](results/full-corpus-long72k-prefix-v1/source-audit.json) ·
[Audit code](results/full-corpus-long72k-prefix-v1/audit.py.gz).

### Source and crop coverage through 80k

The source ledger records **1,280,000** target slots and **425,965**
ordinary-photo draws through update 80,000. Of the **90,778** ordinary
photos, 62,853 have five visits and 27,925 have four. The median fifth
crop adds **1.23%** of the cached image, and the five crops together
cover a median **84.20%** in that subset. The fifth crop adds zero new
cached pixels for 10,060 images. Coverage uses cache rectangles before
augmentation.

The audit verifies the published 72k source prefix, the fixed source
order and draw seeds, and 32 additional saved conditioning chunks.
[80k source audit](results/full-corpus-long80k-prefix-v1/source-audit.json) ·
[Audit code](results/full-corpus-long80k-prefix-v1/audit.py.gz).

### Fifth photographic epoch at update 85,233

The executed ledger completes the fifth ordinary-photo pass at update
**85,233**. Through update 85,250 it records **1,364,000** target slots
and **453,999** ordinary draws. All **90,778** ordinary photos have five
visits and 109 already have a sixth. The fifth crop adds a median
**1.22%** of the cached image, and the five crops together cover a median
**84.24%**. The fifth crop adds zero new cached pixels for 14,528 images.
These measurements use cache rectangles before augmentation.

The audit verifies the 80k prefix and 21 additional saved conditioning
chunks. The [86k checkpoint review](full-corpus-long86k-native.md) binds
the next verified prefix and its separate image-quality results.
[Fifth-epoch source audit](results/full-corpus-long85250-prefix-v1/source-audit.json) ·
[Audit code](results/full-corpus-long85250-prefix-v1/audit.py.gz).

### Observed source and crop coverage through 30k

The running 100k schedule records 480,000 example slots through
update 30,000. There are 160,479 ordinary photo visits and 8,383
reviewed photo visits. All 90,778 ordinary sources appear, with
69,701 visited twice and 21,077 once. The source prefix audit checks
all draw offsets and data seeds against the fixed order and all
120 saved conditioning chunks. The first 20,000 logged step rows
match the archived prefix byte for byte.

The second ordinary visit uses a different cached crop rectangle
for 69,688 of the 69,701 repeated photos. Across those second visits,
the 10th, median and 90th percentile rectangle intersections over
union are 0.266, 0.634 and 0.851. Only 694 pairs are disjoint.
These rectangles precede geometry and sensor corruption. The 30k
checkpoint write is logged, and quality is assessed on the declared
immutable milestones.
[30k source, crop, and conditioning audit](results/full-corpus-long30k-prefix-v1/publication.json).

### Second ordinary photo pass

The second full ordinary photo epoch completes at update 33,985.
By the saved 34k update, the run records 544,000 example slots.
There are 181,674 ordinary photo visits and 9,479 reviewed visits.
All 90,778 photos appear at least twice in the ordinary stream,
with 118 already seen a third time. Of the second visits,
90,757 use a different cached crop rectangle. Median rectangle
overlap is 0.634 by intersection over union, with 926 disjoint
pairs. The audit rechecks the two 30k byte prefixes and the
original conditioning chunks, then verifies the draw order and
all 136 saved chunks through 34k. The native 50k quality review
waits for the immutable state.
[Second-epoch source and crop audit](results/full-corpus-long34k-prefix-v1/publication.json).

The long arm also retains its10k state
`6cd409de7ac06d27e528fcd3c9e70944eb03fd75e74f1a59fb342359b5d765a2`.
[Independent actual-prefix comparison](results/full-corpus-control20k-camera-v1/long-control-source-identity.json)
checks all10k source/crop/data-seed rows against control10k,apart from their
declared different order-header hashes. First160k order positions,all40
conditioning chunks and all3 RNG states match. Native/paired individual IDs
remain unlogged; full GPU sample hashes stay in the running phase until close,
so this is not an all-noise-tensor or quality equivalence claim.

The earlier [first-epoch/18k receipts](results/full-corpus-execution-followup-v1/actual-first-epoch.json)
remain preserved snapshots.

The100k arm uses a100k cosine horizon, LR1e-5→1e-6 with100-step warmup. The
separate control anneals over20k. Checkpoints20k/50k/100k on the long trajectory
measure progress under its long schedule; comparison to the separately annealed
control does not isolate compute from schedule. Complete Adam/EMA/Python/CPU/
CUDA RNG, global data counters and immutable epoch payloads remain in checkpoints.
No planned milestone resets the learning-rate schedule or observation sequence.

## Current-model execution qualification

Three fresh native256/B16/BF16 mixed-domain checks each execute75 updates and
a valid two-update resume, with25 warmup and50 timed updates. All91 model and
EMA tensors,89 Adam states and their steps are finite; the official backbone
stays frozen/unchanged. All five sampled complete input witnesses at steps
1/2/6/76/77 match across policies and worker settings. No held-out quality
score is computed by these optimizer checks.
The later [six-model CPU quality review](training-execution-quality.md) now
compares their77-step EMA states and10k raw/EMA. Strict0/fast0 faint means differ
only0.000215 dB at77, with source-specific gains/costs. This short comparison
does not establish long-run equivalence.10k raw is worse than EMA on all three
review means; selecting raw does not repair the faint regression.

|Execution / workers per loader|Measured patches/s|Loader wait fraction|
|---|---:|---:|
|Strict /0|14.816|9.75%|
|Throughput /0|24.963|12.64%|
|Throughput /2|23.975|0.56%|

The timed window includes loaders, sensor preparation, forward/backward, Adam
and EMA; it excludes initialization, warmup, final checkpoint/audit and resumed
suffix. Observation tensor hashing is outside the timed window. These are one
short window per setting on this GB10, not a batch-size optimum or promised
full-run speedup. Zero workers is the selected setting: two workers reduced
waiting but did not improve total throughput. Both production arms use the
qualified throughput policy, BF16 neural compute and existing FP32 physical maps.
Training-quality effects still need evaluation.

The separate production logger then passes six actual mixed-domain updates and
two resumed updates. It verifies all91 loaded tensors before the first learned
forward, records actual shot/read/WB/matrix inputs and checks global steps6→8.
These updates are discarded; production initializes from untouched V120.

## Actual allocation, records and monitoring

The controller starts the long100k arm for1000 updates, allocates the GPU to
three separate2000-update context probes and the matched20k control, then
resumes the saved100k state for99,000 further updates. This allocation was fixed
before production. It provides early evidence on both user-requested directions
without resetting the long trajectory. All stages are sequential, with bounded
memory/runtime and explicit PID/creation-time ownership; failures stop rather
than silently retrying a training trajectory.

The first1,000 updates completed in750.565 seconds of measured worker time
(752.911 seconds including controller overhead), with16,000 target examples:
477 Commons,262 native and261 paired batches. The photographic draws visited
5,045 distinct source IDs across5,294 visits and5,047 source/crop-box pairs.
The immutable raw/EMA/Adam/RNG checkpoint is
`e72da50252f1de4c76ecf7985d940d4094a6e8b7de0dca50269cc39eb0ba8c54`.
This is an interrupted trajectory milestone, not a completed100k endpoint.
The new allocation adopts that state and does not replay its prefix.

The20k control later retained a complete6k raw/EMA/Adam/RNG state, then stalled
while redundantly writing `best.pt`. [The explicit recovery](full-corpus-checkpoint-recovery.md)
preserves the failure/partial bytes, retains best by atomic link to the completed
last checkpoint, and continues the remaining14k in a new frozen output tree.
The long arm subsequently resumed its original1k state. Old worker/controller
identities describe their historical allocation; the recovery has new bound
ownership. The20k horizon is now complete; the100k horizon continues. Training completion
alone establishes no quality gain.
The first actual post-repair7k checkpoint has since passed complete raw/EMA/
Adam/RNG validation and atomic last/best retention. A later first-last write
stalled at14k, after complete13k. [CPU checkpoint recovery](full-corpus-checkpoint-cpu-recovery.md)
preserves that evidence and resumes the remaining7k without changing learning
math; the lost1k segment is recomputed with identical source/conditioning.
Its actual14k and subsequent20k checkpoints saved and passed complete
raw/EMA/Adam/RNG validation. The long continuation is
[actually observed after resume](results/full-corpus-control20k-review-v1/long100k-resume.json).

The retained [10k EMA review](full-corpus-control10k-review.md) is numerically
complete and all32 boards have actually been viewed, including both GFX families.
Its53,506 distinct photo IDs/56,363 visits exceed the old20k continuation's
42,086 IDs, but faint fidelity regresses on all four materials. The selected
flat-color mean bias improves while centered spatial RMS worsens. This midpoint
does not isolate coverage from reviewed quota/execution or fill broad panels.

The [completed20k targeted review](full-corpus-control20k-review.md) uses110
matched inputs/220 CPU roots and actually views all26 boards, including both GFX
families and native GT triplets. Ordinary/shadow means improve slightly; faint
mean nearly returns to V120, with higher spatial error for three materials.
The [ADC-bin follow-up](adc-bin-consistency.md) is a separate opt-in zero-noise
physical diagnostic, not a new training result or default.

The20k [full427/known/unseen benchmark](full-corpus-primary-admission.md) and the
[scene-arm benchmark](whole-scene-context-primary-admission.md) are running on
CPU. Complete comparable results and the broader96,075-block analysis remain
pending;32-photo monitoring and four-material means do not fill those gaps.
No history point is added; V120/V131 remain the latest complete three-panel
measurements. Concurrent physical CUDA input export and CPU reviews preserve
training recipes/ownership, but wall time is not exclusive or claimed identical
to execution without concurrent activity.

The scaling worker records CPU source/crop metadata each update. Actual
shot/read/WB/matrix tensors are transferred in250-update batches; complete
GPU batch hashes are sampled initially and every1000 updates. This avoids
per-update full-target GPU readbacks while retaining replay and coverage
witnesses. Source visits, distinct cache crop boxes and corruption RNG/conditioning
records remain separate. Crop bounding boxes precede later geometry; they are
not a count of independent native pixels. ADC/noise-free recipes remain labelled
rather than counted as positive-noise examples.

A fixed32-photo lightweight monitor replaces the previous eight-image panel.
Broad photo/camera, phase-correct weak increments, quiet coarse luma/chroma,
adverse colour and native comparisons remain required at useful milestones.
The controller retains immutable phase-end checkpoints and step1k/5k/10k/
20k/50k/100k states. New performance reports need at least two unresized native
noisy/restored/exact-GT triplets with identical coordinates/transforms and full
checkpoint/noise/exposure provenance.

Both standing real-photo families remain required: DSCF3879/3880 sky, building,
foliage and coarse fence; DSCF3842/3835 both cab mesh ROIs/profiles/JPEGs.
Independent ISO100/AHD/JPEG references differ in aperture, exposure and motion,
are **not exact GT**, and receive no pixelwise reference scoring. Local caches
only; original media remain read-only.

## Preserved setup failures and retention correction

Two initial profile admissions stopped before model construction: the first
used an outer run directory refused by the frozen worktree's output guard;
the second lacked project/lock/license metadata needed by the full trainer's
source snapshot. New admissions correct those locations/inputs and retain both
original source trees, logs and terminal receipts. No optimizer/noise/model
trial preceded those refusals.

The discarded logger check exposed a separate retention mistake: its six-step
receipt referenced mutable`last.pt`, which the planned resume replaced. Original
receipts/condition arrays and the final eight-step model/Adam/EMA/RNG state are
retained, but those intermediate six-step checkpoint bytes are unavailable.
No rerun attempts to recreate them. Before production, every phase end was
changed to an immutable hardlink, in addition to the milestone snapshots.
The explicit retention addendum is part of the admission publication.

After the first1,000 production updates, the context handoff failed while
creating its output directory, before any context model construction or data
draw. A new frozen context admission creates parent directories, includes the
canonical auxiliary mosaic loss omitted by the original discarded preflight,
and saves complete Adam/RNG/draw-index state. All three corrected preflights
pass. Original sources, failures and the RGB-only qualification are preserved;
none are relabeled as production context training. The remaining allocation
starts the corrected context arms and retains the original scaling schedule.

Root:`.cache/experiments/full-corpus-scaling-v3/`.
Production plan`872a1d16ef80f6673e90b5893534d3c4ca9e529a2baf8d9f289c13d450ac8ddc`.
Remaining-allocation plan`4954e1a6d221d2244210ddfaa923477723f3fd47a89cb5ad85e2ea19502b16f3`.
Parent SHA256`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`;
DINO`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
