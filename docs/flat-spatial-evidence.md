# Clean-flat spatial-error supervision

**V181 is training; image quality is unmeasured.** It keeps the completed
[V180 local-evidence architecture](local-phase-evidence-comparison.md), initial
checkpoint, data and 900-update recipe. One added loss targets spatial error
inside clean flat neighborhoods. The 98 neural source files, all seven existing
loss terms and the existing target mask stay unchanged. V180's measured mesh
gain and its quiet-field costs remain the current evidence.

[Loss](../scripts/flat_spatial_objective.py) ·
[Independent CPU tests](../tests/test_flat_spatial_objective.py) ·
[Native CUDA probe](../scripts/admit_flat_spatial_objective.py) ·
[Continuation](../scripts/train_flat_spatial_evidence_trial.py) ·
[Eight-term auditor](../scripts/audit_flat_spatial_evidence_trial.py) ·
[Actual preparation, probe and launch evidence](results/v181-flat-spatial-preparation-v1.json).

The previous goal turn made concrete progress: V180's completed comparison,
exports, native viewing and audits are published. Its EMA mesh response rises
15.93% over global V178, but quiet spatial RMS rises 0.79–1.05%, worsening
31/32 inputs. That result motivates this loss experiment; it does not meet the
joint detail/quiet-field goal. No earlier successful training is repeated.

## Loss and its scope

The existing clean-target mask selects centers whose truncated 17×17 target
neighborhood has at most 1 DN16 range in every camera-RGB channel. Existing
V180 traces show mean eligible coverage of 69.0% in mesh batches, 50.3% in weak
detail, 52.2% in photo, 90.8% in mixed and 68.9% in flat batches. Lack of mask
coverage is therefore not a sufficient explanation for the remaining spatial
error. These are training-mask statistics, not held-out quality measurements.

For each selected center and channel, let `e = (output − target) / (4/65535)`.
The added term is the whole-image mean of
`mask × (sqrt(1 + Var_window(e)) − 1)`, using the same truncated 17px window.
It enters the loss at weight **0.25 × the existing domain weight**. The old
seven-term total is computed first, preserving its FP32 operation order.

The term removes each channel's local mean error. It can penalize fine false
texture and variation within broad mottle while leaving constant RGB error to
the existing absolute, common-error and regional-DC terms. It supervises actual
target differences, including sub-DN gradients that qualify for the mask;
it does not replace those targets with constants. A strong textured window
excluded by the clean mask receives no new spatial penalty. Shared model
parameters can still trade detail for quiet error, so actual comparisons are
necessary.

Centered FP64 moments and separable truncated means avoid large color-bias
cancellation and materialized-window memory. The final extra loss is FP32 for
FP32 model outputs. Units are training weights, not a calibrated uncertainty
estimate. Target masks enter only after inference. No inference gate, hard
cutoff, new parameters or noisy-flat guarantee is introduced.

## Implementation evidence

All **55 focused CPU checks** pass, including 25 new checks and the existing
flat-anchor/weak-gradient tests. Independent NumPy window enumeration verifies
values and analytic derivatives, including borders and windows larger than the
image. Descent tests remove false texture or recover an actual sub-DN wave.
Constant color errors remain free of spatial penalty, mask coverage retains
its weight, and all seven existing terms and the mask remain exact.

The first run had 24 passes and one test-harness failure: pytest tried to turn
a requires-grad tensor into NumPy. Comparing its scalar value fixes that test;
the loss implementation and tolerances did not change. Source/log are preserved.
An initial dependency check also rejected a canonical import where a sealed
module was required, before Torch/output creation. The corrected check runs
the completed V180 gate in its own process with frozen import paths.

The actual CUDA probe uses two cached native four-image batches: mesh then
mixed. It starts from V172's real 141 Adam states at 900 plus a zero local
adapter with no Adam history. Both updates pass all 142 finite/nonzero tensor
gradients, independent eight-term FP32 totals, and CPU/GPU comparison of the
new loss and **6,291,456 output-gradient coordinates**, with zero observed
differences. Genuine model/Adam/EMA/CPU-CUDA-RNG restoration occurs between
updates without replay. Counts are two wrapper/frozen/matching/projection
calls and ten samplers; peak allocation is about 6.28 GiB. The existing sampler
atomic-backward warning remains under the warn-only deterministic setting.

Independent CPU inspection strictly restores both actual probe checkpoints,
network clocks 901/902, adapter clocks 1/2, EMA and frozen weights. It initializes
no CUDA and repeats no neural forward. These probes do not initialize training.

## Matched training and comparison

The original continuation starts again from the same V172 checkpoint and zero
adapter used for V180. It adds 900 updates/3,600 noisy images over the same
1,000 cached rows, with 100 ADC skips. Domain weights, LR schedule, EMA, sampler
and architecture stay fixed. The bound training body changes only its objective
import; seven helper bodies are exact copies of the completed engine. CPU
warm-start proof retains all old moments/network EMA, with adapter EMA initially
zero. Actual row8 checkpoint restoration has passed and resumed at row9.

Outputs use the external SSD to preserve the local reserve. The trial keeps
both raw/EMA endpoints and plans the complete 822-case review, exact frozen/ADC
checks, the same 36 native cases and independent training/quality audits. The
completed V180 endpoints and earlier useful strengths remain comparisons;
they are not rerun. Atomic sampler backward prevents a bit-exact retraining
claim, and this reused development stream supplies no blind/seed uncertainty.

Both protected GFX families, JPEGs and siblings remain excluded from training.
Only cached arrays/parents are read; no new source/noise, parent/DINO inference,
RAW decode or original/dataz access occurs. Future quality reports must retain
main-scene sky/building/foliage/fence, both fine cab ROIs/profiles/JPEGs and at
least two unresized noisy/restored/exact constructed-GT triplets. Independent
ISO100/AHD/JPEG references stay qualitative, not exact GT or scoring targets.
