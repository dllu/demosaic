# First trained DINO low-rank trial

V49 tests the [verified query/value adapters](dino-low-rank-adaptation.md) at
rank4 against the completed V47 control. There are73,728 new parameters in24
DINO attention projections; all21,596,544 original foundation parameters remain
frozen. This changes which context representation can learn, with the original
full-resolution CNN and all physical camera information retained.

The [seed50 preflight](results/dino-lora-v49-preflight.json) verifies all71 common
portable tensors and initial predictions exactly in FP32/BF16/FP16 for all four
CFAs. A discarded actual-batch fixture at16×256×256 backpropagates nonzero
adapter gradients, updates AdamW, and confirms unchanged original foundation
hashes. Peak CUDA allocation is7.44GB for that fixture, not a throughput result.
Earlier portable-checkpoint/EMA and exact optimizer/RNG resume fixtures remain
linked in the receipt. No source implementation changed for this trial.

[V49 recipe](../configs/dino-qv-lora-b16-v49.yaml) and V47 share V43 first1000 EMA,
seed50, fresh AdamW/EMA, batch16, LR3e-5/planned3000 and a first gate at1000
updates. Commons4/native128/paired manifests,25/25/50 domain mix, augmentation,
original8× validation, pinned DINO revision, camera representation and precision
remain fixed. New Commons pixels are excluded. Only adapter rank and run/notes
differ. Default rank0 keeps prior behavior.

Reuse V47 only after exact training-source bytes and all41 logged input/target
hashes verify. The workflow then scores known/unseen paired development data,
all427 photographs/16 procedural sources and the full102MP standing GFX scene,
with two exact synthetic-GT crops plus paired/GFX native references and verified
RGB16 outputs. Model selection waits for that complete review. V43 step2000
remains the experimental photographic reference; no new quality gain is claimed.

The [guarded workflow is now running](results/dino-lora-v49-launch.json) in
frozen checkout `d3cc159`. Its first logged observations match V47 exactly.
The archive driver and plan are under `/mnt/external/demosaic/runs/`; live status
is `dino-lora-v49-workflow.json`. Training stops after1000 updates before any
model selection. This is the first quality trial of the adapters; it is not
the still-needed fresh DINO presence/absence attribution experiment.
