# Optional ConvNeXt pyramid prepared while original long training continues

The original fresh no-context/ViT-S/ViT-B schedules remain isolated in frozen
source `8580a4e` and continue sequentially toward 10,000 updates with their complete
model/EMA/AdamW/RNG state. No new GPU work was started. The first arm is past
6,775 with finite observations; final quality and convergence remain unknown.
Commons originals continue downloading into quarantine; active memberships stay
fixed. Other users' GPU jobs remain untouched.

Investigated genuine DINOv3 ConvNeXt-Tiny as a spatially finer feature source.
Approved access works. Pinned revision `10d30274b4d445111e2d5bf75ac93bbd94db274b`,
111,299,216-byte weights match Hub LFS SHA256 `bd30a945…339cb2`, and the downloaded
license is byte-identical to the existing DINOv3 copy. Actual CPU extraction
confirms four finite rectangular stage maps at 1/4, 1/8, 1/16 and 1/32 resolution.

Implemented an optional top-down pyramid with 262,336 trainable feature-fusion
parameters around the 27,820,128-parameter frozen encoder. Three zero-gated
offsets enter the CNN at half/quarter/eighth resolution. Earlier additions keep
the control's hidden dtype; the existing explicit FP32 middle policy stays
matched. Padding is cropped in its original coordinate system, not squeezed
into a smaller rectangle. Default ViT/absent-context computation and common
initialization are preserved. Learned state is portable; malformed or missing
state fails. Packed/input/LoRA combinations are deliberately unsupported.

The complete CPU suite passes 488 tests with 8 CUDA skips in 96.74 seconds. Tests
cover initial common state/RNG and exact mixed-precision values/gradients,
nonzero gates/laterals, all encoder weights frozen, rectangular coordinates,
fusion placement, portable reload and clear configuration errors. The initial
full run caught an unnecessary new keyword on older trunks; preserve their
original call signature. No full CUDA validation claim is made.

The first genuine-weight CPU preflight incorrectly labeled the project's
FP32-only CPU precision helper as BF16. Preserve its receipt with a correction;
do not cite it as BF16 evidence. The explicit full-size BF16 second attempt
proved prohibitively slow and was stopped only in its owned CPU process before
completion. The corrected third protocol uses an asserted small actual-BF16
fixture and FP32 for native256/updates/reload. The linked validation receipt
now records successful completion with identical initial predictions, two finite
discarded updates per arm, nonzero learned gates, unchanged encoder weights and
exact FP32 portable reload. It initialized no CUDA context. This is engineering
evidence; actual GPU/FP16 and complete-state restart checks remain.

[Architecture and evidence](../docs/dino-convnext-pyramid.md),
[CPU validation](../docs/results/dino-convnext-pyramid-cpu-validation.json),
[prepared V58 recipe](../configs/dino-convnext-pyramid-fresh-b16-v58.yaml).
V58 uses the original fresh Gaussian prior, seed 48, batch 16, LR 1e-4/planned 10,000,
Commons 40,170/native 128/original paired 32 and unchanged augmentation/validation.
Backbone, fusion and parameter capacity change together. Require the preceding
long review and real CUDA/FP16/native256/restart checks before actual training;
then matched numerical, weak/flat, exact-GT native, full GFX and additional-camera
review. No quality improvement or model promotion is claimed by this preparation.
