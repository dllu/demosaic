# V95 follow-up: train with ADC sample consistency

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

This is a prospective quality experiment, not an improved-model result.
V43 was the reference for this experiment. The completed
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

## Execution status, October22 local time

Both production arms completed4,000 updates and their owners exited.
Independent saved-state audits pass for every retained model/EMA/Adam state and
training/validation trace. Each arm processed64,000 images, including4,751 ADC
images; all161 logged batch hashes match across domains. All four discarded
CPU/CUDA preflights also passed, with exact24-batch correspondence per device
pair. Final4k EMAs remain primary; both validation-best states are step3000 and
remain diagnostic. The [training completion and evaluation launch receipt](results/v95-adc-training-complete-and-evaluation-launch-v1.json)
retains the audits, checkpoint identities, exact-EMA projected V98 export and
actual controller launches. The [preflight receipt](results/v95-adc-training-preflights-and-launch-v1.json)
retains the separate discarded-run evidence.

Frozen training plan:
`.cache/quality-first-20261020/V95-ADC-matched-training-v1/plan.json`, SHA256
`e2d4f9acc2c96b854612ccb933d0d2d20ab36f114cef184009fbdee57df5540a`.
Artifacts: `/mnt/external/demosaic/v95-adc-training-20261021-v1/`.
The completed [CPU handoff](results/v95-adc-quality-handoff-launch-v1.json)
audited the training states and launched the serial seven-panel evaluator.
`scripts/evaluate_v43_quality_trial.py prepare ... --adc-training` requires
both projected endpoints and unchanged final4k initializer lineage. Root status
updates do not change the frozen prospective plan or its criteria.

The photo worker has exited. All111,636 cases pass coverage/invariant checks;
[independent photo auditing](v95-adc-training-quality-review.md#completed-photo-panel)
finds V99−projected-V98 +.02880 dB, below the fixed .03 dB requirement, with
ADC photographic SSIM −.0020322. Both criteria fail. Known/unseen numeric audits
are also complete. The [full seven-panel and lower-noise native review](v95-adc-training-quality-review.md)
is complete: high-noise color RMS and retention of V95's weak-detail response
also fail. No model is promoted
or extended from the final4k endpoints; V43 was the reference for this experiment.

Sample-fidelity coverage derives from explicit priors:1,772 ADC observations
per projected model in photo/procedural evaluation,224 in the analytic grid,
and588 in the color grid. Positive camera/GFX priors require zero ADC selections.
The completed photo stage checks114,270,400 valid measured values per model,
with maximum error2.98e-8 sensor units, below the1e-6 limit. Empty valid support
reports no numeric maximum. These diagnostics preserve the original reference
invariant schema and establish neither unmeasured-color accuracy nor RGB16
output precision.

The [photo auditor](../scripts/audit_adc_photo_contrasts.py) checks the complete
nine-method grid before reporting all-condition, ADC-only and positive-noise
contrasts, separately for photographic/procedural sources. `--expect-adc-pair`
requires projection on both endpoints; matched training lineage is checked
separately. Its [historical CPU rehearsal](results/v95-adc-photo-contrast-preparation-v1.json)
and the [full-panel observer rehearsal](results/v95-adc-full-panel-fidelity-preparation-v1.json)
remain implementation evidence. The current
[completed photo receipt](results/v95-adc-completed-photo-review-v1.json)
records the actual V98/V99 result and independent Decimal/scalar replay.

The [secondary native-photo controller](../scripts/evaluate_v95_native_photo_conditions.py)
started only after all seven primary panels and both owners exited. It completed
36 triplets over the first four sources and two fixed crop cases at ADC-only,
ISO100 and ISO12800. All108 saved scalar rows match the full suite exactly;
actual native review covers these triplets and all96 primary triplets through
180 unchanged native cells. Both controllers and every owned worker have exited.
The [complete receipt](results/v95-adc-complete-quality-review-v1.json)
binds counters, ADC fidelity, independent scalar/float64 array audits and the
actual native/GFX findings. The [helper preparation](results/v95-adc-native-detail-preparation-v1.json)
retains the separate69-test packaging rehearsal. V43 was the reference for this study;
this failed final4k recipe receives no extension or speed work.
