# Experimental fixed RAW and residual units

Two constants are now recorded in `ModelConfig` and portable checkpoints. Both
default to1, preserving existing recipes. The [optimization tests](packed-isotropic-residual-units.md)
motivate a full-data trial; improved photographic quality remains untested.

```yaml
model:
  restoration_backbone: packed-isotropic
  camera_conditioning: true
  isotropic_raw_gain: 32
  isotropic_residual_scale: 0.03125
```

The gain multiplies only four neural RAW features before both stems. Original
log-variance/CFA/WB/matrix features retain their values. The residual scale
multiplies only the learned head output before adding the original bilinear
signal. Both operations stay IEEE FP32 under hidden autocast. Capacity,
physical output/loss units and the DINO preview remain unchanged. There are no
per-image statistics, clipping or resampling.

These constants change optimization and a nonzero trained model's function;
start a new trial fresh. Checkpoint save/reload retains them, and training resume
requires identical configuration. Older checkpoints with missing fields use1.
Nonfinite/nonpositive values, booleans and nondefault units on other backbones
are rejected.

Configured gain32/residual÷32 matches the isolated prototype exactly for
nonzero-head predictions, all gradients and three AdamW updates. All-CFA odd
rectangles retain FP32 signal and16-bit changes under BF16 autocast. Actual
interrupted CPU training reproduces weights, EMA, Adam moments and Torch/Python
RNG, and rejects changed units. Default/scaled DINO tests cover common initial
weights/RNG and nonzero-context portable reload.

Both actual40k EMA checkpoints with older metadata also match archived code
bit-for-bit on64 frozen training observations each/native34×50:652,800 RGB
values. Both heads have3456 nonzero weights and DINO has96 nonzero gates.
All852 no-DINO and1045 DINO/restoration/backbone tensors stay unchanged.
[Receipts](results/packed-isotropic-unit-default-CPU-v1.json) record current
source/test/checkpoint/fixture/output hashes and exited CPU owners. This is CPU
FP32 compatibility at recorded contexts, without a full-frame CUDA or quality
claim.68 unique focused cases are covered across the targeted runs; Ruff passes.

The completed [batch-learning study](packed-isotropic-batch-learning.md) and original
CPU coordinate study retain frozen code. Existing recipes/checkpoints stay
unchanged; no new quality model is promoted.
