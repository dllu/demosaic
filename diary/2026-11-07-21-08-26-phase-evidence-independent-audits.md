# Prepare independent checks for phase-evidence training and quality

Recorded: 2026-11-07T21:08:26-08:00 (America/Los_Angeles).

V178 has an independent CPU auditor for its matched control/evidence trial.
Training and quality still await V175's complete GPU pipeline and the native
CUDA admission. The previous turn made concrete progress by implementing and
freezing that matched trial; current process inspection confirms V175 training,
its completion watcher, the admission watcher and the single matched-trial
controller are all still live at their original PID/create-time identities.
There are no phase-failure receipts. No successful prefix is restarted.

All 34 new audit checks pass, including deliberate corruption of source/parent
bindings, masks, FP32 totals, LR/EMA/update clocks, sampler/projection counts,
ADC observations, frequency evidence and qualified real references. Summary
validation requires every numeric metric column and compares means through
independent Decimal arithmetic. CPU checkpoint restoration explicitly ignores
saved CUDA RNG through the restore API and compares its bytes separately;
tests forbid both CUDA RNG APIs while preserving distinct old/new Adam clocks.

Two structural fixtures adapt the existing V172 trace without new inference.
They preserve its real terms, masks and input bindings while explicitly
simulating V178's LR/EMA/network clocks and adapter call bookkeeping. All 2,000
rows and 1,800 recorded FP32 loss totals pass; eight corrupted copies reject.
This is not actual V178 training or a trajectory replay. Six existing profiles
also exercise metadata geometry/suppression on 144 saved peak records from 18
images. Their bins/powers are real saved measurements, while cross/validity
fields are simulated. No spectral coefficient is recomputed in this check.

One actual V172 checkpoint is loaded on CPU. Its 141 Adam states remain at 900,
and strict raw/EMA state hashes match the original loading path. Only EMA key
prefixes and the initial-plus-new update metadata convention are adapted for
the audit helper; weights, moments, steps and saved RNG bytes are untouched.
There is no evidence-arm checkpoint, actual neural forward or optimizer update.
The preparation peaks at 750 MiB RSS with CUDA uninitialized.

The audit source and tests are sealed in an additive two-file work directory,
outside the unchanged 713-file trial snapshot. Actual frozen imports resolve
the original trial dependencies. Source binding accepts only a prepared plan
that includes the fixed draft receipt; both actual audit entries currently
reject the absent plan. Intentional CPU prerequisite rejections are not failed
scientific attempts. No actual training/quality audit receipt is manufactured.

After actual completion, training checks cover both complete traces, ten
checkpoints, distinct adapter/network clocks, raw/EMA weights, saved RNG and
all frozen tensors. Quality checks cover all 3,288 durable method/input/frozen/
ADC bindings and compare the input-only spectral metadata exactly across raw
and EMA. All 144 retained native RGB arrays and 144 residual arrays are checked
with independent metric and addition reductions. Other new outputs retain
journal fingerprints/in-process metrics, not a full array archive. Metadata
agreement is not independent spectral recomputation or calibrated confidence.
Real ISO100/AHD/JPEG references remain unscored. Actual viewing and paired
detail-versus-sky comparisons are still required before any quality conclusion.

All 97 current neural files, 96 original V175 sources, 18 sealed completion
helpers and existing machine receipts remain unchanged. Work uses cached
project/external data only; original photos and unavailable source storage
remain untouched. Existing model recommendations and crop comparisons remain
available while actual V175 and V178 quality is pending.

[Audit commands and limits](../docs/phase-evidence-training.md#independent-audit-preparation) ·
[Preparation and exact evidence](../docs/results/v178-matched-trial-audit-preparation-v1.json) ·
[Publication verification](../docs/results/v178-matched-trial-audit-publication-verification-v1.json).
