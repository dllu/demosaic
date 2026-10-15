# Pretrained restoration with DINOv3: V28 experiment

The frozen eight-step Gaussian RGB comparator recovers stronger texture and
substantially better synthetic-noise scores than V16. It still has real-camera
regressions and is costly. V28 tests whether a trainable pretrained restoration
trunk, CFA measurements and frozen DINOv3 context can supply a stronger single
pass. **The [first 1k review](pretrained-rgb-v28-review.md) shows progress, not a promoted model.**
See [the fixed-prior numerical/native-crop review](stabilized-gaussian-review.md).

The RGB trunk retains the tensor names/topology of the verified original RGB
DRUNet: widths 64/128/256/512, four residual blocks per stage, strided convolutions
and transposed-convolution upsampling. It is not a new DRUNet architecture.
Its pretrained restoration weights are strictly loaded, then trainable. The
upstream [Noise2VST source](https://github.com/sherbret/Noise2VST) and KAIR weights
are pinned in the [source/weights receipt](results/gaussian-color-source-and-weights.json).
The copied/adapted topology carries both original MIT notices in
`third_party/gaussian/`; wheels include these notices and DINOv3's license.
Fresh training refuses to silently substitute random pretrained weights.
Only original neural tensor weights are transferred: the source receipt's
four-step comparator schedule and variance-stabilization procedure are not used
by V28. A frozen step-zero checkpoint preserves the actual initialization for
later before/after comparisons.

The joint wrapper uses these project-specific changes:

- Native Malvar camera RGB, normalized by each image's own affine range; a
  different image in the batch cannot alter that range. Signed measurements and
  unclipped predictions are retained. This is linear RGB, **not GAT/HQS**.
  Constant RGB uses a unit scale; nearly flat tiles have an eight-sigma range
  floor so ADC clipping/quantization cannot amplify the noise input excessively.
- A spatial marginal-noise proxy from the supplied variance maps replaces the
  uniform Gaussian noise-level input. Correlation/heteroscedasticity after
  demosaicing are not assumed to match the original Gaussian training model.
- A zero-initialized 21→64 projection adds original normalized CFA measurements,
  phase/color masks, log RGB variance, white balance and camera matrix at the
  first native-resolution stage. It exposes the observed data instead of asking
  the network to infer CFA geometry from an RGB preview alone.
- The genuine pinned DINOv3-S/16 supplies three intermediate feature maps through
  the existing adapter and a zero-initialized fusion gate at 1/8 RGB resolution.
  Its 21,596,544 backbone parameters remain frozen; only its adapter/gate train.
- First/last RGB projections and the measurement projection stay IEEE FP32,
  including backward arithmetic; deep features use BF16 training/FP16 evaluation.
  The high-precision first skip preserves weak native variations. Physical
  feature construction and affine output conversion remain IEEE FP32. Native
  RGB16 support is not inferred from a floating output dtype alone.
- Auxiliary clean CFA supervision samples the actual RGB prediction, so both
  tasks share a physically consistent reconstruction.

The model has 54,829,760 parameters, 33,233,216 trainable. It uses the existing
calibrated paired-CFA and synthetic linear/rendered/gradient/highlight losses.
[The V28 recipe](../configs/dino-pretrained-rgb-v28.yaml) uses an expected mix of
50% Commons/procedural, 25% paired RAW and 25% binned native-RAW synthetic batches,
with noise-free cases, optical/geometry augmentation and broad camera/exposure
simulation. All 40,170 eligible Commons training sources are available; the
separate validation/final sets and standing GFX scene/siblings are excluded.
Native low-ISO RAW targets are low-noise estimates, not exact noiseless RGB GT.

The first review stops at 1,000 steps of the planned 5,000-step schedule, batch4,
LR1e-4 and per-step data RNG/observation hashes. A later matched no-DINO control
is needed to attribute any gain to the foundation features. This trial changes
the restoration initialization, backbone and data proportions relative to V16;
it cannot isolate any one of them.

Tests cover exact original-weight inference compatibility, observed CFA/mask
geometry for all layouts, batch-independent physical features, odd tile geometry,
sub-16-bit identity/ramp preservation under autocast, gradient flow through the
new adapters with a frozen backbone, strict checkpoint round trips and invalid
configurations. The complete CPU run passed 217 tests with eight CUDA tests
skipped. A genuine DINOv3 CPU training smoke completed Commons and native-RAW
batches with finite loss/gradients and saved a checkpoint; this is execution
evidence, not quality validation. The complete CUDA-enabled suite subsequently
passed **226 tests in 18.08s**, including deterministic restart with spawned
data workers. A genuine DINOv3 BF16 CUDA backward check retained FP32 output,
nonzero fusion-gate/measurement-adapter gradients and no frozen-backbone gradients.

The same CPU training run resumed from step2 to step4 with its original
pretraining lineage and optimizer state retained. The built wheel was inspected
for the new implementation and all three upstream license notices. The workflow
validated all six full-frame RGB16 files and completed a step-zero photographic
screen. Its first in-process training attempt stalled after step1 waiting for
forked data workers. Only that owned attempt/workers were terminated. Training
now runs in a fresh CLI process with `worker_start_method: spawn`. The first
1,000 steps completed with the same first-batch fingerprint; matched development
and full 102 MP evaluation are in the [first review](pretrained-rgb-v28-review.md).
Training completed 5k; see the [full 427-photo and real review](pretrained-rgb-v28-5k-review.md).
The [matched V29 trial](stabilized-rgb-v29-review.md) evaluates explicit shot/read
variance stabilization with the same initial neural tensors. No GFX images were fitted
or used in training. See [startup/validation evidence](results/pretrained-rgb-v28-startup.json).

Reproduce with the locked environment after obtaining the pinned original
RGB weights listed in the receipt:

```bash
source scripts/env.sh
uv run --no-sync demosaic train configs/dino-pretrained-rgb-v28.yaml --stop-after 1000
```

The run archives its actual source, MIT/DINO notices, data manifests, verified
original weights and initialization lineage. A portable restoration checkpoint
contains the trainable RGB trunk/adapters; it does not require the external
Gaussian implementation to load. Frozen DINO weights retain their pinned
upstream dependency, as with existing models. Promotion requires matched native
crops, complete development evaluation, real GFX review and 100 MP RGB16 output;
passing software tests or a short training run does not meet that gate.
