# Matched continuation draft for phase evidence

The V178 training/review code is implemented and CPU drafted. **No training has
launched.** Actual [CUDA admission](phase-evidence-admission.md) must finish
before the draft can become a prepared GPU plan. This is a controlled test of
the [phase-evidence variant](phase-evidence-matching.md), not a new quality result.

[Training and review](../scripts/train_phase_evidence_trial.py) ·
[Adam/EMA state handling](../scripts/phase_evidence_training_state.py) ·
[State tests](../tests/test_phase_evidence_training_state.py) ·
[Native renderer](../scripts/render_phase_evidence_trial.py) ·
[CPU draft and checks](results/v178-matched-trial-CPU-draft-v1.json).

## Same starting history and budget

Both arms start from the actual V172 raw model, Adam moments at step 900 and
saved EMA. The control retains local-noise matching; the evidence arm adds the
zero 3,120-weight projection into its 39 input coordinates. All 188 existing
model tensors, 141 old Adam states and 141 network EMA tensors match at startup.
The new adapter has no allocated Adam history and a zero EMA tensor.

Each arm makes one further pass over the same 1,000 cached scene/calibration/
target/observation rows: **900 additional updates/3,600 images and 100 ADC skips**.
No noise, geometry, photo source or parent/DINO output is regenerated. All
seven loss terms and domain weights stay unchanged. Both use the same row-based
50-row warmup, peak learning rate 1e−4, cosine decay to 1e−5, AdamW decay 0.01,
gradient clip 1 and EMA rule. The evidence arm changes the feature path and adds
3,120 parameters jointly; it is not an isolation of information from capacity.

This is separate from V175's larger fresh-noise recipe. V175 will remain an
explicit comparison with its own strengths and costs; it is not the matched
control for this one-pass fork. A later useful initializer can change without
reinterpreting the current fixed experiment.

## Correct clocks and EMA

After 900 new updates, the existing 141 network tensors reach Adam step 1800.
The new adapter reaches step 900, not 1800. Its optimizer group uses the same
effective learning-rate schedule. EMA includes both network and adapter keys;
it starts with V172's old network EMA and a zero adapter, then follows the
unchanged whole-model decay using 900 inherited plus new updates.

The 13 CPU tests use actual AdamW updates to check distinct clocks, exact old
moments/EMA, source-checkpoint and independent-arm storage, genuine restore,
subsequent clock advancement, and rejection of incomplete/wrong-shape/wrong-
dtype EMA before mutation. Deep-copying optimizer payloads avoids sharing CPU
moment storage between the checkpoint and both arms. This is important even
though actual GPU loading usually creates new storage.

The completed real-checkpoint CPU draft verifies all 141 old Adam states at 900,
all old weights/EMA exact in both arms and the new adapter at no-history/zero.
It loads one existing checkpoint, performs no actual matching/DINO/sampler
forward or optimizer update and does not initialize CUDA. The frozen actual
`prepare` entry rejects the absent admission result before importing Torch;
the training entry rejects the absent prepared plan before any CUDA call or
training claim.

Checkpoints are planned at rows 8/250/500/750/1000. The row 8 checkpoint must be
genuinely restored into a fresh module, with model, Adam, EMA and CPU/CUDA RNG
exact, then continue at row 9 without replay. Separate control/evidence trace,
launch, status, result and failure files preserve ownership and completed work.
All trainable gradients must be present/finite, while frozen parameters receive
none. Atomic sampler backward retains its existing warn-only nondeterminism;
the trial does not promise a bit-exact retraining trajectory.

## Complete quality and native comparisons

The implemented review covers **all four raw/EMA endpoints on all 822 fixed
inputs**: 3,288 component/frozen calls, 3,000 matching calls, 15,000 samplers and
1,500 new evidence projections. It checks 3,288 exact V169 replays and 288 ADC
identities, streams fingerprints/metrics/evidence metadata, and retains RGB plus
residual arrays for 36 native cases. EMA evaluation loads the new adapter EMA
alongside the network EMA; it never silently evaluates a raw adapter as EMA.

The renderer retains identical source coordinates, 160×160 crop pixels and
display transforms. It plans 48 comparison boards plus 24 noisy/restored/exact
constructed GT triplets, covering all four endpoints. Boards retain V175 EMA,
V172 EMA, V169 EMA, stronger V161 detail, periodic detail and the appropriate
exact or qualified references. Both protected GFX scenes include sky, building,
foliage, coarse fence and both fine cab windows/priors/JPEGs. Independent ISO100
and JPEG references remain qualitative, not exact GT or pixelwise score targets.

A completed CPU renderer fixture exercises all 72 figures/24 triplets/18 sheets
using only existing V172 predictions and V174 source pixels. Its V175-shaped
tags are simulated. Every header says **CPU LAYOUT FIXTURE / NO V178 QUALITY**;
no fixture image is published as a model comparison. It checks 16,588,800 new-
method crop channels against independent display conversion and preserves the
old pixels/ROIs without resizing. One fixture triplet was viewed for layout
only. The actual trial has no scores, predictions or figures yet.

After actual training/review, independent numerical/checkpoint/native audits
and actual viewing are still required. Report detail response together with
absent/blank error, quiet total/spatial/DC error, flat full/coarse error, natural
band fidelity and the standing real-photo weaknesses. Keep useful gains and
costs visible without claiming blind generalization or noisy-sky safety from
this reused development suite.

## Storage and launch

New trial checkpoints and native arrays are planned under its local
`.cache/quality-20261107/V178-phase-evidence-trial-v1/artifacts/` directory,
with a 2 GiB forecast and 48 GiB local reserve plus margin. This uses recovered
local headroom while preserving the external 111 GiB reserve and existing
V175/admission forecasts. No old evidence is removed or moved.

Formal preparation must bind the actual passed CUDA admission and V175's
completed scores/figures, verify that all 97 neural source files match the
admitted variant, and check current resources. Launch wrappers use frozen code
and gate each stage on the preceding actual owner/result. The control runs
before evidence, and both complete before review. No stage automatically
restarts a failed scientific prefix. The current CPU draft does not authorize
code to bypass missing admission or results.

A single CPU controller is now waiting for the admission watcher to terminate
successfully. It will inspect both actual admission checkpoints and their
142 fresh Adam states, nonzero adapter weights, frozen tensors and restore
evidence before preparing the trial. It waits for resources, runs each matched
stage once, renders native comparisons, and stops for actual image viewing.
Its source and launch identity are sealed; the publication receipt records the
observed waiting state. No V178 training or quality worker is running yet.
