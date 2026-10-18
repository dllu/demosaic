# Same-source, same-seed V54 replay

[V57](../configs/dino-paired-replay-b16-v57.yaml) repeats historical V54's first
1,000 updates using its original frozen `b62c996` package. Only the run directory
and explanatory notes change. This is a repeatability check, not a new model
proposal, a different training seed, or an estimate of training-seed uncertainty.

The [V55 weak-source gate](weak-texture-v55-review.md) and
[V56 input-adapter gate](dino-input-v56-review.md) lose natural-photo and known
primary means without a clear native advantage. Their matched-source intervals
describe evaluation-source variation. Independent CUDA training is not bitwise
deterministic, even with common initialization and matching logged inputs.
An unchanged control replay checks the scale of procedural variation before
attributing small differences entirely to either intervention. One replay
provides a descriptive comparison, not a calibrated variance estimate or proof
that a particular difference comes from numerical nondeterminism.

The retained V43 step 2,000 EMA, fresh AdamW/EMA, seed 52, batch 16, LR 3e-5,
100 warmup updates and planned 4,000-step schedule stay fixed. So do the
reviewed paired83/native128/Commons40170 manifests, domain proportions,
augmentation, loss, physical noise, frozen DINO and model precision. No weak
source or input adapter is introduced. The new run stops at 1,000 for review.
The original V54 step 1,000 and 4,000 snapshots remain untouched.

The controller verifies the original package/config/manifests/parent identities,
requires all 41 logged input hashes to match, and recomputes both models and
baselines on known/unseen, full427, analytic/flat and full GFX suites. Native
triplets and full RGB16 checks precede interpretation. It starts only after
the V56 owner has actually exited and its complete native review is published.
Evaluation-only scripts copied into the old worktree are explicitly hash-pinned;
the training package stays exactly the original source.

The frozen source had already completed the original validated V53/V54
schedules and full reviews. This replay does not silently adopt the newer model
code or restart any existing run. The unfinished original fresh no-context/S/B
10,000-step schedules remain separately preserved and audited; completing them
can follow this repeatability check. No model or data recipe is promoted here.

The [actual launch receipt](results/control-replay-v57-launch.json) records the
live controller, original source/config identities and matching logged batches.
The first input hash matches exactly; the first CUDA loss differs by about
1.80e-6. Its cause is not isolated, and this observation alone does not explain
the eventual quality difference. The [complete review](control-replay-v57-review.md)
now finds replay−original photo −0.04346 dB, known primary −0.05946 dB and
nearly unchanged unseen primary. All 41 logged inputs, model configuration,
source bundle and final RNG states match, but restoration weights differ.
This observed spread makes small single-trajectory claims less decisive; it
does not estimate seed variance or prove the cause of any earlier difference.
All 46 native triplets and eight full RGB16 outputs verify. No model promotion.

The separate [directional first-step execution diagnostic](directional-firststep-execution.md)
now captures a genuine initial model and first clean batch and passes an exact
CPU two-pass forward/backward check. Three CUDA profiles are queued after the
current reviewer exits. This does not explain the historical variation or
establish long-run GPU repeatability.
