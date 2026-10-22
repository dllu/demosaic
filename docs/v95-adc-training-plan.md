# V95 follow-up: train with ADC sample consistency

This is a prospective quality experiment, not an improved-model result.
V43 remains the working reference. The completed
[V96/V97 review](v95-flat-palette-quality-review.md) shows color shifts and lost
detail on nearly clean inputs; more training and a wider flat palette did not
repair them.

The existing [ADC-only projection](adc-projection-v52-review.md) restores valid
measured samples without introducing learned parameters. Its historical
inference-only review improves ADC photographic PSNR but retains edge and
procedural-SSIM tradeoffs. That does not prove that training through it helps.
Here the network learns the remaining unmeasured colors while the physical
operator preserves nonclipped observations on explicit shot=read=0 examples.
Every positive shot or read prior bypasses the projection; ISO100 is not ADC-only.

## Matched training

| Setting | V98 control | V99 constrained training |
| --- | --- | --- |
| Initializer | Final V95 stage20k EMA | Same exact EMA |
| Learned architecture | Original V43 | Same tensors/parameters |
| ADC projection during training | Off | On |
| Data | Curated 88,484 Commons, original native128/paired32 | Same |
| Augmentation | Zero PSFs; weak .15, photographic attenuation .25 | Same |
| Flat/noise-free fractions | Original .10 flat, narrow palette; .10 ADC | Same |
| Budget | Seed58, B16/native256, BF16, 4,000 updates | Same |
| Optimizer | Fresh AdamW/EMA, LR2e-6, warmup100 | Same |

The lower LR is shared and is a deliberate change from the earlier 1e-5
continuations; comparisons against those runs do not isolate projection.
The previous V95 schedule ended at 1e-6. All other training/data/loss settings
remain V95's. No new loss, noise prior, synthetic generator or architecture is
introduced. All 47 numerical source files must remain byte-exact to V95.
Commons/native/paired observations must match across arms in both discarded
preflights and all recorded production batches, including Commons. Each
production first24 observation hashes must match its own CUDA proof.

The final 4k EMA is primary. Retain 1k/2k/3k and validation-best checkpoints as
diagnostics; do not select a better intermediate. Original validation remains
eight sources, seven conditions/four CFAs. Training validation does not replace
the full quality panels. Holdouts, protected final scenes and the standing GFX
scene/siblings remain outside training. Originals and frozen corpus membership
remain unchanged.

## Separate training from the known inference effect

The primary learned comparison is **V99 projected versus V98 projected**.
V98's evaluation control is an inference-only export of its final EMA with the
same existing ADC flag enabled. Its learned tensors must remain exact and its
training lineage must be preserved. Comparing V99 with raw V98 would mix
training effects with the already-known inference projection and is diagnostic
only. Original V43/V95 policies remain reference methods. Any parent comparison
also changes training budget and is not an isolated training-policy contrast.

Run the full 427-photo/16-procedural suite, known/unseen measured-CFA panels,
carrier/flat/color grids and standing GFX plus highlights, in fresh IEEE FP32.
Use the common projected policy for both trained endpoints, original shared
observations, RawNIND input-only adapters and classical controls. Native photos
must include at least two unchanged 100% noisy/restored/GT triplets per model;
also view ADC/ISO100 fabric, building and GFX foliage/fence. References for real
captures remain approximate or separately captured, not exact GT.

For a useful training benefit, require projected V99−V98 full-photo PSNR at
least +.03 dB with positive paired-source 95% lower bound, and a nonnegative
positive-noise-only photo mean contrast. Known/unseen CFA mean losses must not
exceed .03 dB each. Retain all scene intervals and adverse source tails.
Require ADC photographic/procedural SSIM means not to fall versus the common
projected control, and no individual ADC carrier gain loss greater than .05.
The brighter .18-level/2%/16px high-noise response must at least retain V95's
fixed-grid gain; flat-field spatial RMS must not exceed 1.25×V95. Both ADC and
high-noise p95 channel bias and worst centered color RMS must not exceed V95
or the projected control. Native fabric color/detail must improve without new
fringes or GFX failures. These are fixed development decisions, not blind
generalization or training-seed uncertainty. No single passing mean promotes
a model. Do not extend a failed final4k recipe or start speed work from it.

## Execution and checks

Use the shared bounded controller's explicit ADC-training mode. A frozen copy
of this plan, recipes, numerical code and helper dependencies governs the run.
First perform discarded actual 24-update CPU and CUDA preflights for each arm:
same initializer/DINO hashes, fresh empty optimizer, finite gradients/states,
correct ADC/noisy selection, exact paired/native/Commons input correspondence
and checkpoint reload checks. The worker records how many training images and
explicit ADC examples were observed. Actual forward hooks must preserve valid
ADC measurements within 1e-6 sensor units; this is not a full DN16 output
qualification. Those counters/checks are execution evidence, not restoration
quality. The independent saved-state auditor permits only the
declared ADC flag and retains the distinction from exact parent configuration.

Require 48 GiB available RAM and 64/384 GiB free root/external storage, stable
for 60 seconds before each worker. Active RAM floor 24 GiB; disk-only shortages
suspend only the owned process group and resume the same worker after the
original thresholds recover. Record actual resource readings every 2 seconds;
waits are bounded, failures preserved, no automatic retry or other-project
process management. No production/default checkpoint changes before full review.

## Execution status, October 21 local time

All four discarded proofs completed: 24 actual updates per arm/device,
96 training/DINO forwards over 816 images, including 54 ADC images. Each
CPU/CUDA pair has all 24 observed batches identical across every data domain.
Independent checkpoint/config/lineage/EMA/Adam/finite-gradient checks pass.
Candidate CUDA hooks preserve valid samples within 5.97e-8 sensor units.
Both production arms completed all 4,000 updates and their owners exited.
Independent CPU audits pass for every retained model/EMA/Adam state and the
training/validation traces. Each arm processed 64,000 images, including 4,751
ADC images; all 161 logged production batch hashes match across domains.
The final4k EMAs remain primary; both validation-best checkpoints are step3000
and remain diagnostic. These are execution checks, not model-quality findings.
The
[preflights and historical launch observation](results/v95-adc-training-preflights-and-launch-v1.json)
retain the preflight evidence. The
[completed training and evaluation launch](results/v95-adc-training-complete-and-evaluation-launch-v1.json)
records the independent audits, final checkpoint hashes, exact-EMA projected
V98 export and actual live evaluation/crop-controller observations.

Frozen training plan:
`.cache/quality-first-20261020/V95-ADC-matched-training-v1/plan.json`, SHA256
`e2d4f9acc2c96b854612ccb933d0d2d20ab36f114cef184009fbdee57df5540a`.
Artifacts: `/mnt/external/demosaic/v95-adc-training-20261021-v1/`.
The run uses the frozen prospective copy of this plan; this status addition
does not change that archive. Full evaluation was prepared with
`scripts/evaluate_v43_quality_trial.py prepare ... --adc-training` after
both owners exited and independent saved-state audits were written as
`independent-V98-training-audit-v1.json` and
`independent-V99-training-audit-v1.json` in the training-plan directory.
Preparation produces the exact-EMA V98 export, retains its training lineage
and requires the projected policy explicitly for both new endpoints. Focused
tests reject unrelated architecture/precision changes. The primary photo GPU
worker is running; complete quality and native review remain pending.

Full evaluation now also checks sample fidelity on every declared projected
endpoint. Coverage is derived from explicit priors: 1,772 ADC observations per
model in photo/procedural evaluation, 224 in the analytic grid and 588 in the
color grid. Known/unseen camera and GFX priors are positive, so require zero
ADC selections. Valid measured channels must agree with the input within
1e-6 sensor units. Empty valid support reports no numeric maximum. These
diagnostics are separate from the unchanged reference invariant schema and
do not establish unmeasured-color accuracy or full RGB16 output precision.

The [CPU observer preparation](results/v95-adc-full-panel-fidelity-preparation-v1.json)
passes 35 focused checks and replay on all 588 saved V95 ADC color fields
(38,535,168 valid CFA values). It detects input inconsistencies in the
unprojected arrays; the existing projection reduces measured-sample error to
at most 5.83e-11 in this fixed replay. All 588 positive-noise fields are skipped.
No model inference, new noise or quality claim follows; actual V98/V99 full
stage execution remains pending.

## Queued audits and full evaluation

At 21:17 PDT on October 21, a CPU-only handoff queue is waiting on the original
training controller and worker. It requires the exact plan/controller identity,
all six completed phase/arm receipts and exited training owners before running
the two independent saved-state audits. It then prepares the common projected
comparison from frozen helpers and launches the existing serial seven-panel
evaluator. The evaluator owns its GPU workers and resource controls after
handoff; the queue exits. There is no training restart or automatic retry.

The [launch receipt](results/v95-adc-quality-handoff-launch-v1.json) records
71 passing focused checks, four actual frozen CLI checks and all 47 numerical
files byte-exact to the training archive. Queue plan SHA256:
`f0a8cc521b9c1b6033e69e1ce5be842a5b5d78fa62cf054319f508290c3a04ff`.
At this observation neither the audits nor any new quality panel had started.
Training quality, native-crop inspection and the promotion decision remain
pending; V43 remains the working reference.

The [prepared photo auditor](../scripts/audit_adc_photo_contrasts.py) will report
all-condition, ADC-only and positive-noise-only contrasts separately, keeping
photographs and procedural sources separate. It first verifies the complete
nine-method score grid and summary arithmetic, then averages within each source
before resampling. `--expect-adc-pair` requires the projection flag on both
primary endpoints; matched training lineage remains a separate audit.

The [CPU preparation receipt](results/v95-adc-photo-contrast-preparation-v1.json)
records 16 passing frozen tests and a rehearsal on completed V43/V95/V96/V97
scores. Independent Decimal/scalar arithmetic rebuilds 10,632 source-metric
means and checks 72 contrasts, agreeing within 7.11e-15. A real CLI check rejects
the historical unprojected pair when common ADC inference is required.
The rehearsal is not V98/V99 quality evidence. Its separate live observation
records V98's final4k checkpoint and the running V99 owner; no new evaluation
panel had started.

The [secondary native-photo helper](../scripts/evaluate_v95_native_photo_conditions.py)
now accepts the same projected V98/V99 comparison while preserving V43/V95
reference policies and both final4k initializer identities. It retains the
first four full-suite sources and two fixed native crop cases, at ADC-only,
ISO100 and ISO12800: 36 planned triplets. It checks measured-sample fidelity
on ADC inputs and requires positive-noise conditions to retain positive priors.
All seven primary panels and their owners must finish/exit before its GPU
worker starts; the full suite remains primary.

The [native-helper preparation](results/v95-adc-native-detail-preparation-v1.json)
passes 69 frozen checks and actual packaging/CLI checks, including the crop-board
dependency. The historical preparation rehearsal starts no controller or
worker. The new secondary diagnostic is now prepared and its CPU controller
is waiting for all seven primary panels and exited owners. Its GPU worker has
not started. The [execution receipt](results/v95-adc-training-complete-and-evaluation-launch-v1.json)
records both actual launches. Complete native review remains pending; helper
checks alone establish no crop-quality result.
