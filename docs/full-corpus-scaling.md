# Full-corpus scaling and whole-scene context training

**Larger-corpus training has begun: the100,000-update trajectory has saved its
first1,000 updates.** All three whole-scene comparison arms have completed;
the fresh matched20k control is now training, before the remaining99k updates.
Their [first matched native review](whole-scene-context-native-review.md) finds
no convincing new fine crossings; the [completed64-source study](whole-scene-context-development64.md)
adds small quiet-coarse gains and mixed detail/color costs. No larger-corpus endpoint gain is claimed.
V120 remains the general recommendation while milestone evaluation is pending.
This implements the [training-scale review](training-scale-pipeline-review-2026-11-17.md)
and complements the [scene-context experiment](whole-scene-context-next-test.md).

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

These are **planned source-order counts**, not completed training coverage.
The first complete ordinary-photo epoch occurs at step17,039. The first320k
source slots of the two orders match exactly. In the100k ordinary sequence,
12,765 sources have five visits and78,013 have six; reviewed visits are additional.
The schedule is generated once, not restarted at each milestone. Repeated visits
use fresh global sample indices, spatial augmentation, camera/exposure and
per-step sensor RNG. Correlated/overlapping crops are not counted as disjoint
native detail or newly independent scene layouts.

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

Training completion, numerical evaluation and actual native viewing are tracked
separately. No new full427 or known/unseen-camera result is available, and the
32-photo monitor is not a comparable panel. Neither scaling horizon is complete;
the finished scene arms' [broad evaluation is running on CPU](whole-scene-context-primary-admission.md).
Its canonical physical-only CUDA input export ran briefly alongside training;
neural evaluation is CPU-only. Training PID, recipe and schedule were preserved;
wall time is not exclusive and resulting weights are not claimed bit-identical
to execution without concurrent activity. The PSNR registry/
chart therefore remains unchanged. V120/V131 remain the latest
completed comparable broad measurements. Both standing fence reviews and native
triplets are pending for scaling endpoints; the separate scene2k arms now have
their [completed native comparison](whole-scene-context-native-review.md).

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
