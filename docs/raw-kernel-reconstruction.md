# Experimental reconstruction from centered RAW differences

An optional reconstruction head now makes one useful physical property explicit:
**a clean constant-color Bayer field retains its calibrated camera RGB, whatever
features and kernel coefficients the network predicts.** CPU tests verify this
to floating-point precision. This is an architectural constraint, not evidence
of better denoising. The option is default-off; V63/V64 retain their unchanged
frozen model source and recipes. A separate [bounded head warmup](raw-kernel-warmup-v65.md)
has completed its first review after CPU/CUDA engineering checks. Its poor
noise removal prevents promotion; the numerical invariant alone is insufficient.

[Executed CPU checks, frozen candidate source and actual-parent state receipts](results/raw-kernel-CPU-preflight.json).
[Implementation](../src/demosaic/raw_kernel.py).
[Physical invariant and integration tests](../tests/test_raw_kernel.py).

## Motivation and distinction

The [V61](sensor-mean-v61-first1k-review.md) and
[V62](sensor-mean-v62-first1k-review.md) losses reduce some flat-field color bias
while sacrificing other accuracy and weak detail. This prototype instead limits
how the decoder can change constant-color signals. It does not apply a fitted
mean correction to an existing restored image.

The [2026 ACKN paper](https://people.csail.mit.edu/cjbisc/burst/burst_paper.pdf)
predicts reconstruction weights for neighboring sensor samples from an encoder
and sample geometry, with signed weights normalized by their absolute sum.
Our inference from its equation 1 is that this normalization alone does not
enforce an identity RGB response to constant per-color samples. That is not a
claim that the authors' trained network has a color defect. The implementation
here is independent: discrete, single-frame Bayer reconstruction from centered
differences, without their continuous-coordinate MLP, burst alignment, code or
weights. Existing DINOv3/DRUNet features condition our coefficients.

## Reconstruction rule

Let `a_c(p)` be an actual sample of color `c` in the 2×2 Bayer cell containing
output pixel `p`. One green phase is chosen as the reference; both greens remain
available as samples. Let `s_mk(p)` be a same-color sample from a 3×3 packed
neighborhood, after phasewise box averaging with packed windows 1, 5 or 17.
The 67-channel context concatenates the existing native decoder features and
its three normalized RGB outputs. A zero-initialized 1×1 convolution predicts
324 coefficients, bounded individually by `tanh`.

For output color `j`:

```text
RGB_j(p) = bilinear_j(raw)(p)
         + sum_m,k tanh(coeff_jmk(features(p))) * (s_mk(p) - a_color(k)(p))
```

For clean spatially constant camera RGB `x`, every sample difference is zero
and the bilinear baseline equals `x`. Each learned term has zero response to a
constant of its input color. This remains true for arbitrary network features,
including features conditioned on camera/WB, noise and frozen DINOv3 context.
It assumes calibrated phases share the same value for a given color, including
the two green phases. Unmodeled sensor phase-gain differences are a limitation.

Box means are evaluated as a center sample plus averaged neighbor differences,
separately horizontally and vertically, with replicated boundaries. Constant
phases therefore remain exactly constant in FP32 rather than accumulating small
rounding offsets in a long sum. Input centering, coefficient prediction and
filter application run in camera-linear IEEE FP32, even under autocast. No
output clamp or target-dependent calibration is added.

This adds **22,032 parameters**. The existing RGB tail remains trainable because
its outputs condition the kernel; they never directly add an RGB offset to the
reconstruction. The final output bypasses the existing inverse-VST prediction;
the original noise/VST/camera construction still conditions encoder features.
Native processing is required; packed processing and the separate ADC projection
are rejected rather than combined with this experimental path.

The identifying model options are `raw_kernel_reconstruction: true` and
`raw_kernel_windows: [1, 5, 17]`, added to an otherwise compatible native
pretrained-RGB configuration. These are experimental options, not a released
training recipe or a recommendation to replace a trained model's output head.

## What has actually been verified

The targeted CPU suite passes **43 tests**, with one CUDA test skipped because
CUDA is explicitly hidden. Tests cover all four CFA patterns, arbitrary strong
coefficients/features on constant RGB, negative and above-white values, exact
zero-head bilinear behavior, sub-16-bit variations, fixed-feature per-color
offsets, gradients through sensor input/context/head, the actual RGB trunk/tail,
odd image sizes, checkpoint round-trip and invalid support/path combinations.
The complete CPU suite subsequently passes **528 tests, with 9 CUDA-related
skips**. Its first run found one test-oracle precision issue: the new comparison
against a long FP32 average was switched to an FP64 reference with the original
bounds unchanged. Across 100 random cases, the implementation's maximum error
against FP64 is 1.49e-7; a direct FP32 pool reaches 1.73e-6. Production model
code was unchanged by that test correction, and the original failed log remains
in the receipt.

The genuine-parent CPU check uses completed V60 step4000 EMA, SHA256
`1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e`.
It compares the actual frozen legacy package with the archived candidate package
with the option disabled on two native 256 photo observations and one odd-sized
126×158 variant. All three full FP32 predictions match bit for bit.

With the option enabled, every existing EMA tensor loads exactly and the only
new parameter tensors are the coefficient convolution's weight and bias. The
actual DINOv3 backbone stays frozen. Zero coefficients give **bilinear output,
not the mature parent's restoration quality**. Four discarded actual CPU updates
match two plus two resumed updates exactly in all nine whole-state fields,
numeric logs and input hashes. All 93 model/93 EMA tensors and 91 AdamW states
are finite. Commons, native-RAW and paired-RAW domains are exercised.

Those fixtures use batch1/native 64/FP32, zero workers, forced smooth Commons
and two validation images. Their short losses and validation values are not
restoration-quality evidence. The executed package, operator, inputs, logs and
full states are archived. This CPU fixture started no new GPU inference or training while
the owned V63/V64 workflow ran.

A separate read-only check of that saved experimental EMA reconstructs every
tensor, including the actual DINOv3 backbone, exactly through the portable loader.
Two full natural-photo predictions match the manual EMA reconstruction bit for
bit. Across 64 clean analytic cases (four colors × four CFAs × two conditioning
profiles × two CPU precisions), maximum absolute RGB error is 5.96e-8, including
negative/above-white numerical range tests. CPU BF16 autocast changes deep
features while the reconstruction stays FP32. No noise was added to those
constant fields; they do not establish unbiased restoration of noisy fields.

## Completed CUDA engineering check

The [actual CUDA execution and independent saved-state audit](results/raw-kernel-CUDA-preflight.json)
have completed after the V63/V64 workflow owners exited. The archived
[operator](../scripts/preflight_raw_kernel_cuda.py) executes the frozen 411d source,
not the later head-only option. All 127 archived files and 11 inputs verify.
Original [preparation/queue evidence](results/raw-kernel-CUDA-preflight-queue.json)
remains historical evidence rather than the execution result.

The genuine V60 full 4k EMA loads every old tensor exactly, actual DINO stays
frozen, and initial GPU BF16 output equals bilinear exactly. Seven discarded
B16/native 256/BF16 updates cover Commons, paired and native data with seed49,
LR1e-5/warmup200 and planned 20k. The fixture forces real Commons, uses workers0
and two validation images; it does not alter either completed data arm.

All 93 model/93 EMA tensors and 91 AdamW states are finite. Model/optimizer/EMA/
Python/Torch/CUDA RNG reconstruction succeeds. Portable/manual EMA predictions
match exactly on two full native 256 photos under FP16 and BF16, including every
saved tensor and actual DINO. A native 256/B1/BF16 probe gives finite nonzero
trunk/tail/head gradient norms 5.79e-6/3.15e-7/.06128; DINO has no gradients.
Sixty-four clean native 64 constant fields (four colors/four CFAs/two conditioning
profiles/two precisions) have maximum RGB error 5.96e-8. No noise is added to those
fields. Peak CUDA allocation is 21.328 GB, not total unified RAM or throughput.
A separate CPU audit verifies the saved checkpoint, source/config/data, all seven
all-domain logs, finite state and saved prediction hashes/shapes.

These are engineering results from discarded updates. They do not establish
restoration quality, noisy-field unbiasedness, convergence or deterministic CUDA
optimization after restart. Those prototype checks did not launch a production
joint trial; the later [V67 stage](raw-kernel-phase-joint-v67.md) follows completed
V65/V66 quality reviews and its own genuine-parent CPU/CUDA checks.

## Optional head-only warmup

The trainer now accepts **`raw_kernel_only: true`** when the model enables
`raw_kernel_reconstruction`. It freezes every existing restoration parameter,
including the native RGB trunk/tail and DINO projection/gates, and trains only
the coefficient convolution's weight/bias: 22,032 parameters in two AdamW states.
The actual DINO backbone remains frozen. The original training targets and losses
supervise the coefficients; no teacher output, fitted calibration or extra RGB
offset is used. All restoration tensors remain in the checkpoint and EMA.

This provides a declared way to learn the new reconstruction head before joint
training. It does not preserve parent-quality output at initialization: zero
coefficients still produce bilinear. The option defaults off. It cannot combine
with another refiner-only mode or be enabled without the optional RAW head.
Optimizer reconstruction from the saved config applies the same parameter scope.
Changing the scope during resume is rejected before an optimizer update. Joint
training after warmup must initialize a new run from the warmup EMA, with a fresh
optimizer/EMA and separately declared budget; it is not an implicit resume.

[Executed CPU evidence](results/raw-kernel-warmup-CPU-preflight.json) covers the
genuine V60 full 4k EMA, discarded batch1/native 64/FP32 updates, zero workers,
forced smooth Commons and two validation images. All three training domains are
exercised. Every one of the 91 existing model tensors and its EMA stays exactly
equal to the parent; only the two new head tensors change. All 93 model/93 EMA
tensors and two AdamW states are finite. Four uninterrupted updates equal two
plus two resumed updates in all nine saved state fields, numeric logs and input
hashes. Reconstructing the two-state optimizer succeeds, and all manual/portable
EMA tensors, including actual DINO, and two full photo predictions match exactly.
The scope-change resume attempt fails before any update.

With the option disabled, four actual CPU updates exactly reproduce the earlier
411d-source checkpoint's model/config/EMA/optimizer/RNG/step/best fields and all
numeric logs/input hashes. The new source bundle is
`32a330278824bb0b06b27a7b00439d10a3d853966ee3864ceb96a99ff08ae1c0`.
The complete CPU suite passes **534 tests, with 9 CUDA-related skips**; targeted
RAW-head/trainer tests pass 37. These are numerical/engineering checks, not
warmup convergence, GPU memory/throughput or model-quality evidence. The
[head-only CUDA fixture and bounded V65 launch](raw-kernel-warmup-v65.md) now
provide separate execution evidence; trained quality remains pending.
The completed default-route CUDA fixture retains its independent archived 411d
source and has not silently switched to this option.

## Optional direct phase conditioning

The [matched V66 trial](raw-kernel-phase-v66.md) adds a default-off categorical
coefficient bank for four CFA patterns and four native pixel positions, motivated
by the completed V65/standalone-head diagnostics. Its5,184 additional parameters
with the default three supports offset kernel logits, never output RGB. Clean
constant-color invariance remains. The default route retains legacy numerical
behavior, with a newly recorded defaultFalse model_config field.

The actual [CPU/CUDA checks](results/raw-kernel-phase-preflight.json) pass before
the bounded1,000-update trial starts. Full CPU tests pass 543/9 CUDA-related skips;
genuine-parent CPU restart/legacy parity and B16 CUDA finite 94/94/three-state,
frozen-parent, portable EMA, clean-constant and matched-input checks pass. These
do not establish a photographic improvement. The
[completed matched review](raw-kernel-phase-v66-first1k-review.md) subsequently
finds +1.69373dB photo PSNR over V65, with a .97537dB procedural regression and
substantial remaining grain. V66 is not promoted. Its full native/color/artifact
review precedes the separately declared
[V67 joint restoration stage](raw-kernel-phase-joint-v67.md).

## Limits and required next evidence

The invariant is about **clean constant samples**, not unbiased restoration of
noisy fields. Coefficients depend on the noisy input, so correlation between
weights and noise can still shift the restored mean. Individual bounded
coefficients also do not bound the combined filter's noise amplification to one.
Actual false-color, false-texture, highlights and detail tests remain necessary.

This changes the initial output immediately. It cannot be presented as an
identity-initialized refiner or a drop-in improvement to V60. A fair trained
comparison needs a declared new-head initialization/training budget, potentially
training-only head warmup, and must account for that difference from a mature
RGB decoder. Existing field diagnostics motivated the design; they are not blind
quality evidence.

The genuine CUDA/B16/native 256 gradient/state/portable EMA and memory checks have
passed. Both bounded head-only trials completed full photo and measured-CFA
development panels, weak carriers, fixed hue grid and native real-camera review.
The separately initialized V67 stage now trains restoration features and head
together while keeping the DINO backbone frozen. It stops at2,000 on its original
10,000-update schedule for complete quality/native review before any further
continuation. This is not evidence of better joint-stage quality yet.
Reports must include two native noisy/denoised/exact-GT photographic
triplets and all four standing DSCF3879/3880 regions with accurate non-GT labels.
Do not alter the currently frozen data comparison or score protected-final data.
General color repair, trained detail gain, CUDA speed and SOTA remain unproven.
