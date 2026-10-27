# Learned RAW frequency features: V122/V123 training

**Both V122 and V123 completed their original20,000 updates; full endpoint
predictions are collecting.** V123's [exact saved-state continuation](v123-memory-guard-recovery.md)
retained12,249 updates and performed only7,751 more within the original deadline.
Its96 model/EMA tensors and94 Adam states are finite at20k. A legacy91-tensor
assertion stopped the first photo collector before any neural forward; explicit
per-checkpoint counts now allow the96-tensor models, with all inputs/weights and
the original first-stage deadline retained. Failed receipts remain preserved.
The original controller advanced to V123 after the same V122 worker completed.
V122's temporary GPU yield preserved the in-memory training state, without a
restart or checkpoint reload.
These are the first full-budget trials of the [learned frequency input adapter](learned-raw-frequency-features.md).
All four discarded CPU/CUDA checks passed. A
[V1239k midpoint review](v123-midpoint-quality.md) now measures16 retained
material observations and six GFX contexts, with reused controls and native
triplets. It shows no clear detail-recovery gain. Full endpoint PSNR and native
review remain pending. V120 remains the current general recommendation;
V114, V115 and V117 retain their documented uses.

[Original V122 completion receipt](results/v122-frequency-training-complete-v1.json) ·
[Independent saved-state verification](results/v122-frequency-training-verification-v1.json).
All96 model/EMA tensors and five AdamW states are finite at step20,000.
The91 common tensors exactly equal the V115 parent in both model and EMA;
only the3,264-value adapter was trainable. Counts are20,000 prepared batches,
training forwards and optimizer updates, plus640 validation forwards and20,640
encoder calls. Domains match the prospectively declared9,900 Commons/procedural,4,979
paired/5,121 native batches. The CPU verification constructs no model, adds no
forwards and leaves CUDA uninitialized; it does not reconstruct every training
input or establish image quality. The corrected evaluator is collecting both full runs.

[Completed V123 training and final-state verification](results/v123-frequency-training-complete-v1.json) ·
[Zero-forward identity repair and current dependent owners](results/v123-frequency-quality-identity-repair-v1.json).

[Launch and implementation evidence](results/v122-v123-frequency-training-start-v1.json) ·
[V122 recipe](../configs/quality-v115-learned-frequency-only-v122.yaml) ·
[V123 recipe](../configs/quality-v115-learned-frequency-joint-v123.yaml) ·
[Runner](../scripts/train_raw_frequency_trial.py).

## Shared GPU scheduling

Before coordination, V120 updates took about2.46 seconds while both runs shared the GPU.
At that observed rate, V121's next 20,000 updates alone project to 13.7 hours,
beyond its existing 12-hour controller limit. This is a scheduling observation,
not a controlled speed comparison or an image-quality result.

The [owned-process coordinator](../scripts/yield_training_gpu.py) temporarily
suspended only V122's exact worker, leaving its original controller live. It
resumed that same PID after the original V120/V121 controller exited, after
about8.49 hours with the stopped log unchanged.
[Completed same-worker resumption](results/training-GPU-coordination-completed-v1.json).
Its wait-bound/handled-interruption cleanup remains available. Eleven focused tests and an actual owned
subprocess stop/resume/exception check pass. A
[full coordinator fixture](results/training-GPU-coordination-full-process-v1.json)
also verifies same-worker resumption after its dummy priority controller exits.
No model reconstruction, checkpoint
reload, optimizer restart or update-budget change occurs.
[Live-owner and stopped-log evidence](results/training-GPU-coordination-v1.json).

The wait is capped at twelve hours with eight hours reserved inside V122's
existing 24-hour wall limit. Training timing logs include the yielded interval;
they must not be interpreted as inference benchmarks. The active project work
and queued endpoint review continue.

## Question and controlled difference

V119 improved photo PSNR while worsening known-camera performance and its ADC
color tail. The RAW mesh diagnostics found attenuated physical frequency
structure. This experiment tests learned frequency features while preserving
the useful parent's restoration weights, alongside a jointly trained arm.

Both start from final V115 Small EMA, SHA256
`fee5d05c599cb32f5a1e587c31979f040a06152c8e14676481eee83a4ce04d84`,
with the same zero-output 3,264-parameter adapter. Official DINOv3
ConvNeXt-Small remains frozen, hash
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.

| Setting | V122 | V123 |
| --- | --- | --- |
| Trainable restoration parameters | New adapter only: 3,264 | Common restoration and adapter: 32,907,968 |
| Trainable tensors / AdamW states | 5 | 94 |
| Common restoration learning rate | Frozen | 1e−5 |
| Adapter learning rate | 2e−4 | 2e−4 |
| Common model / EMA tensors | All 91 retained exactly | Updated normally |
| Parent, data, seed and budget | Same | Same |

The different base-LR/multiplier representations implement the same adapter
learning rate. Both retain the same warmup, decay, weight decay and gradient
clipping rule. Freezing changes which gradients participate in that rule.
V122 still backpropagates through the RGB trunk to the input adapter.

The adapter produces exactly zero features for spatially constant per-phase
measurements, including after learning. Freezing the common weights therefore
protects that parent behavior. This does not protect noisy or slowly varying
backgrounds, establish better camera color generally, or fix existing parent
errors. V123 tests the quality tradeoff of allowing the common path to adapt.

## Shared data and training

Both use the prepared **90,786-source corpus and fourteen reviewed photographic
regions**, corrected paired32 groups and existing native-RAW cohort. The new
snapshot withholds the individually inspected roofing advertisement; original
V120/V121 cohorts remain immutable. [Source review](current-source-loss-review.md) ·
[Photographic targets](weak-photographic-targets.md).

Settings are seed 66, native 256px/B16/BF16, 20,000 fresh updates, 200-step
warmup, 50% Commons/procedural, 25% paired and 25% native. Only the selected
domain loads a batch. Workers stay at zero and CPU threads at two for these
runs; this is a quality comparison, not a throughput sweep.

Targets retain 4× binning → geometry → final area2 downsampling, zero optical
PSFs, weak textures .15, photographic contrast attenuation .25, reconstruction
epsilon .0003 / paired .0001 and band loss off. Detached source diagnostics use
existing predictions every 100 updates. No DINO feature fit repeats. Standing
GFX3879/3880 and mesh3842/3835 captures, JPEGs and siblings stay out of training.

Compared with V121, this pair changes architecture, training seed and one
withheld source. V122 versus V123 is the controlled scope comparison. Comparing
either to V121 alone cannot isolate an architecture effect.

## Completed implementation checks

Each arm completes 16 fresh and two resumed updates at CPU128/B1/FP32 and
GB10 CUDA256/B16/BF16: nine Commons, three paired and six native batches.
The arms use identical prepared inputs and identical first outputs within each
device setting. These deterministic observations are reused for a controlled
comparison, not independent noise samples for each arm.

Initial shared weights match all 91 parent tensors. V122 retains them in model
and EMA after training; only five optimizer states exist. V123 has 94 optimizer
states. All model/EMA/AdamW values remain finite; gradients reach all five new
adapter tensors. Changed-scope resume rejects before a neural forward. Valid
resume restores step 16 before new steps 17/18, preserving the 16-step files.

Twelve new scope tests pass, including FP32/BF16 learning and constant-field
preservation for all four CFAs. Twenty-three existing optimizer/head-only
regressions pass. Twelve new evaluation-boundary tests reject short, nonfinite,
wrong-scope or drifting frozen states without neural calls.

Production starts freshly from V115; first inputs/outputs must match its CUDA
check. There is no automatic retry or budget extension. Launch requires 56 GiB
available RAM, the CUDA allocator cap is 16 GiB, and the training guard uses
**32 decimal GB** (about 29.8 GiB). The first frozen plan mislabeled that runtime
field as GiB; its configured value and executed bytes are preserved. The public
runner corrects the field name. Disk reserves are 96 GiB internally and 208 GiB
externally. Existing jobs retain their original owners.

## Endpoint evidence

Eight queued single-view FP32 stages evaluate only the new endpoints: all 427
photos, known/unseen measured cameras, weak carriers, color, standing GFX,
highlights and a complete 101.996MP frame. Across both models they declare
9,172 restoration/encoder calls and 28,380 primary/analytic observations.
Earlier controls and input witnesses are reused from retained arrays.

A queued independent NumPy audit checks saved numerical predictions and
prepares two native noisy/restored/exact-synthetic-GT triplets per endpoint.
The evaluator accepts the trainer's actual plan/status schema and verifies
final optimizer steps, finite states and V122's frozen common tensors before
releasing a checkpoint to evaluation.

The [complete review queues](endpoint-quality-review.md) now cover matched
parent/scope contrasts, local photographic-detail analysis, native linear
RGB16 verification and fine green mesh at both existing fixed noise profiles.
These and actual image viewing remain pending after training. Separate ISO100/AHD
references stay labeled **not exact GT**. Useful gains and weaknesses will
update the current guides; successful training or a protected flat-field
invariant alone establishes no quality improvement.
