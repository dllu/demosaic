# Diagnose varied RAW learning and resume original trials

Previous goal turn made progress: completed the full first32k-example review,
published native failure triplets and checked simple CPU/GPU learning. The
SOTA/decisive real-photo RawNIND advantage/10s requirements remain unmet.

The new training-only replay freezes original steps8001–8016:64 examples,
7 Commons/procedural,4 native and5 paired batches. Both actual V71 raw-model
copies restore the original8k AdamW moments and perform512 updates on identical
CUDA-generated arrays. BF16/FP32 MSE ratios: Commons.8541/.8684,
native.9911/.9941, paired1.0250/1.0225. Neither precision fits the varied set
well. Checkpoint/source/fixture checks pass, owners exit and learned weights
are discarded. This is training optimization evidence, not generalization.

Four further BF16 isolation runs use those same frozen training inputs:
single Commons and paired batches reduce MSE to.7033/.7530 of initial; fresh
Adam on all16 gives Commons/native/paired ratios.8736/.9890/1.0092; RAW gain4
gives.8828/.9807/1.0399. The gain divides corresponding stem weights by4 and
rescales Adam moments, preserving initial FP32 outputs bitwise on all16 cases.
Its exploratory value comes from a descriptive CPU feature-scale inspection,
not a quality sweep. No broad fix is established. No optimizer reset, feature
gain, precision, architecture or loss change enters production. All these
learned weights are discarded; original8k checkpoints stay exact.

The original matched no-DINO/DINO pair now resumes full state to an explicit
step40000 review,25% of its original160000-update/640000-example horizon.
Nothing retimes the original cosine/warmup/LR. B4/BF16/seed51, frozen40170
Commons/native128/paired32,4x-geometry-2x and selected-domain loading remain.
The first8k review was only5% of budget; diagnostics found learning on isolated
examples but no universal precision/finite-state/target fault or simple broad
fix. More original training is an experiment, not a promise of convergence.

New branch run directories preserve original8k logs/source/checkpoints and old
review receipts. Frozen source bundle remains50dc11ec5c906fbbc4d3c5b1b530b95acb3b40a5f725d3a622891b2471c21d16.
The controller retains intermediate16k/24k/32k/40k checkpoints and serializes
owners. Final40k publication occurs after the trainer's final save returns,
avoiding its duplicate interval/stop last.pt save. No automatic promotion or
extension beyond40k; protected-final and cached GFX scene/siblings stay excluded.

Actual no-DINO startup verifies all model/852 Adam states/global Torch/Python/
CUDA RNG before the first update and EMA before its first update. All16 actual
first observations match the discarded replay byte for byte, including
Commons/native augmentation across loader workers. No-DINO controller child
1745464/1792274481.29 is live under1745457/1792274479.6; DINO waits for its
completed40k boundary audit. The frozen plan has49 guards/19 inputs. CPU
preflight checks both finite parents, original recipe fields, equivalent
validation-protocol bytes, immutable branch log prefixes and no CUDA init.
The launcher's first preflight used system Python and failed importing torch
before spawning anything; corrected to the venv interpreter. No training restart.

Plan SHA:eb7dd31878e6fb5147025805a85c26b6e5ce27ff9b2ef4b47ea9de2add217d70.
Private status:/mnt/external/demosaic/runs/packed-isotropic-quarter-workflow-v1.json.
Full quality/native review at40k still needs preparation/completion. Old8k
public result JSON is a frozen continuation input: do not mutate it.

Report:docs/packed-isotropic-production-learning.md.
Public receipt SHA:b87a4dbc156213cbe8c220d3c1dbaa496fdfaf84151692ab617059d2e03f33d3.
Validation:all14 numeric table rows independently match saved results; actual
frozen inputs/source, unchanged8k evidence,16 observed fingerprints, startup
restoration and live owners checked. Private operators pass Ruff; git diff
whitespace check follows. No production-code change, so no redundant test-suite
run. Requirements/research/current pipeline status are updated accurately.
