# ADC-constrained V43 architecture training launched

Recorded: 2026-10-21T20:32:09-07:00 (America/Los_Angeles).

Started the [prospective V98/V99 constraint-training study](../docs/v95-adc-training-plan.md)
from exact final V95 EMA, preserving the original V43 learned architecture,
all 47 numerical source files, curated88484 membership and zero-PSF/weak-detail
recipe. Only V99 trains through the existing ADC-only physical projection.
Positive shot/read inputs bypass it. Both use seed58/B16/native256/BF16 and
fresh optimizer/EMA for4k updates at shared LR2e-6/warmup100. That lower shared
LR is a new common setting; older1e-5 runs are not causal controls.

The primary learned comparison is projected V99 versus an unchanged-EMA
projected V98 inference export, with retained training lineage. Raw V98 is
diagnostic; a known policy-only inference gain cannot count as a training gain.
The existing export helper now supports optional lineage retention, preserves
the original off-policy training config in provenance, and leaves the legacy
default unchanged. Evaluation preparation requires completed independent
training audits and explicitly checks both new endpoints' projected policy.
Other architecture fields and all old reference witnesses remain exact.

The shared training worker/auditor allow only the exact declared V99 ADC flag;
they do not silently accept another model change or claim its config equals
the parent's. Added actual ADC-example counts and forward hooks that check
valid measured samples within1e-6 sensor units. No learned layer, physical
source implementation, training loss, noise prior or speed optimization is
added. Gradient tests preserve measured samples while retaining nonzero
unmeasured directions across all four CFAs. An initial fixed1e-7 derivative
bound missed1.19e-7 rounding for random directions above unit magnitude;
the new unit test now scales one FP32 epsilon by direction amplitude. This
does not change an existing DN16 or production fidelity gate.

All55 focused tests pass: projection forward/gradient/selection, exact export
and lineage, narrow model-override validation, reference/policy sensitivity
and bounded resource controls. Actual frozen CLI imports/arguments were checked
before launch, avoiding a repeat of the earlier missing-helper/CLI failures.
No unrelated architecture or precision change is accepted by the evaluation
policy gate. Full endpoint evaluation remains unexecuted until training finishes.

The frozen plan SHA is e2d4f9acc2c96b854612ccb933d0d2d20ab36f114cef184009fbdee57df5540a;
controller4078681/create1792639267.47 runs one worker at a time. Both CPU and
CUDA proofs passed24 updates per arm, with96 discarded training/DINO forwards,
816 images and54 ADC images in total. All24 observed batches match within
each device across every domain. CPU candidate saw one ADC image and preserves
its valid samples within9.31e-10; CUDA candidate saw26 and preserves them
within5.96e-8. Both initial model hash8c8646... and frozen DINO35035b... match
the initializer. Actual source SHA remains
ea9622343d2ad4d9f12ea0089884ad9dcefb87be4ae06f24eacc764829c02d09.

Independent CPU-only loading verifies all four proof checkpoints: finite71
model/EMA tensors each and69 Adam states at step24, exact planned config and
initializer lineage, finite recorded loss/gradient values, and corresponding
input traces. No model construction/inference occurs in that audit. The
[public launch receipt](../docs/results/v95-adc-training-preflights-and-launch-v1.json)
binds the audit, all proof results, tests, frozen plan and an immutable first
three-row production snapshot. It does not pin the growing status/metrics file.
The first actual production input matches the control's CUDA proof; the full
first24 production check remains required at final worker completion.

V98 production worker4081152/create1792639708.56 is live and had passed125
updates when checked. V99 follows serially after control completion. Same
48GiB stable60s launch/24GiB active RAM and64/384GiB disk floors, actual2s
readings, own-process-only disk suspension and no automatic retries. No source
or parent file is modified; GFX/holdouts stay outside training. No quality,
full100MP, speed or SOTA result is inferred from successful preflights.

Publication verification passes: 15 static launch references, 80 local links,
55 focused tests, Ruff and whitespace checks. All 27 training inputs and 69
frozen files remain exact, including the prospective plan copy after updating
the human-facing status. At 20:39 local, the same production owner was live
past step775, with finite logged losses and gradients. Final retained-state
audits and full quality/native review remain pending.
