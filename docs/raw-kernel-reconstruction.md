# Experimental reconstruction from centered RAW differences

An optional reconstruction head now makes one useful physical property explicit:
**a clean constant-color Bayer field retains its calibrated camera RGB, whatever
features and kernel coefficients the network predicts.** CPU tests verify this
to floating-point precision. This is an architectural constraint, not evidence
of better denoising. The option is default-off; V63/V64 continue using their
unchanged frozen model source and recipes.

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
with the option disabled on two native256 photo observations and one odd-sized
126×158 variant. All three full FP32 predictions match bit for bit.

With the option enabled, every existing EMA tensor loads exactly and the only
new parameter tensors are the coefficient convolution's weight and bias. The
actual DINOv3 backbone stays frozen. Zero coefficients give **bilinear output,
not the mature parent's restoration quality**. Four discarded actual CPU updates
match two plus two resumed updates exactly in all nine whole-state fields,
numeric logs and input hashes. All 93 model/93 EMA tensors and 91 AdamW states
are finite. Commons, native-RAW and paired-RAW domains are exercised.

Those fixtures use batch1/native64/FP32, zero workers, forced smooth Commons
and two validation images. Their short losses and validation values are not
restoration-quality evidence. The executed package, operator, inputs, logs and
full states are archived. No new GPU inference or training was started while
the owned V63/V64 workflow runs.

A separate read-only check of that saved experimental EMA reconstructs every
tensor, including the actual DINOv3 backbone, exactly through the portable loader.
Two full natural-photo predictions match the manual EMA reconstruction bit for
bit. Across 64 clean analytic cases (four colors × four CFAs × two conditioning
profiles × two CPU precisions), maximum absolute RGB error is 5.96e-8, including
negative/above-white numerical range tests. CPU BF16 autocast changes deep
features while the reconstruction stays FP32. No noise was added to those
constant fields; they do not establish unbiased restoration of noisy fields.

## Prepared CUDA engineering check

The [actual CUDA fixture is prepared and queued](results/raw-kernel-CUDA-preflight-queue.json),
not yet executed. Its public [operator](../scripts/preflight_raw_kernel_cuda.py)
separates CPU preparation from gated execution. Candidate source, dependencies,
operators, fixture, parent, data and input hashes are archived in
`/mnt/external/demosaic/benchmarks/raw-kernel-CUDA-preflight-v1/`.
The CPU preparation audit imports the real frozen candidate, verifies all 127
archived files and inputs, and independently reconstructs expected trainer source
bundle `411d1669b050b8074d7a9d030b3c42ef1af6764c6f20efbd08ecf5466dc632d8`.
It rejects actual live artifact owner 2060575 before initializing CUDA, creating
a training run, constructing a network or fetching any training batch.

Queue controller PID 2069973, creation 1792211664.76, waits for that exact artifact
owner to complete and exit. This serializes the check after the V63/V64 training,
primary evaluation, statistics/hue and CPU artifact work. It imports the archived
candidate package while the data experiment keeps its original model worktree.
The queue stops for independent review after engineering checks; it launches no
production trial and makes no quality decision.

The pending fixture starts from V60 full4k EMA with the option enabled and checks
that all old EMA tensors load exactly, actual DINO stays frozen and initial GPU
BF16 output is exactly bilinear. It then runs **seven discarded batch16/native256/
BF16 updates**, seed49, LR1e-5/warmup200 and the original 20,000-update schedule.
The seven domains are Commons, Commons, Commons, paired, paired, Commons, native.
It uses original reviewed 40,170-source Commons/native128/paired32 data, workers0,
forced real Commons and two validation images. These fixture overrides do not
change either active production arm.

Intended checks cover finite 93 model/93 EMA tensors and 91 AdamW states, saved
optimizer/RNG reconstruction, exact portable EMA predictions on two natural photos
under FP16 and BF16, and a BF16 gradient probe through the native RGB trunk/tail
and new coefficient head. Sixty-four clean native64 constant cases cover four
colors/four CFAs/two conditioning profiles/FP32 and BF16, including negative and
above-white numerical values, with no noise added. Peak CUDA allocation is
recorded separately from total unified RAM or throughput. These remain pending
checks: preparation alone proves none of their GPU results.

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

Before any production trial: genuine CUDA/B16/native256 gradient/state/portable
EMA and memory checks, followed by the full photo and measured-CFA development
panels, weak carriers, fixed hue grid, false-detail tests and native real-camera
review. Reports must include two native noisy/denoised/exact-GT photographic
triplets and all four standing DSCF3879/3880 regions with accurate non-GT labels.
Do not alter the currently frozen data comparison or score protected-final data.
General color repair, trained detail gain, CUDA speed and SOTA remain unproven.
