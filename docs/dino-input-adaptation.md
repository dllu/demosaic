# Experimental adaptation before the frozen DINO encoder

An optional 6,531-parameter RGB input adapter now precedes the frozen DINOv3
encoder. It passes engineering checks; trained quality is still unproven.
[Genuine-parent GPU preflight and complete test receipt](results/dino-input-v56-gpu-validation.json).

The existing branch projects three intermediate token grids into the CNN's
bottleneck. Its [matched fresh no-context/S/B comparison](fresh-dino-capacity-3k-review.md)
does not demonstrate a context benefit through 3,000 updates. A separate
[training-only preview diagnostic](dino-preview-sensitivity.md) shows that fixed
Wiener filtering helps early feature agreement but can harm middle features.
Neither result establishes that a learned input adapter will improve restoration.
The new experiment tests that hypothesis directly with reconstruction losses.

## Implementation

Set `model.dino_input_adapter: true` with `model.dino: true`. The adapter is
three 3×3 convolutions, RGB→24→24→RGB, with SiLU between them and replicated
boundaries. Its residual is added to the rendered noisy preview before native
16-pixel padding and ImageNet normalization. The last convolution starts at
zero; the initial preview and common model outputs remain exact. Construction
preserves the global RNG so subsequent common layers retain identical initial
weights. The default is false and adds no portable state tensors.

The adapter receives RGB only; no new noise map or teacher is supplied. The
restoration model retains its explicit physical noise conditioning. This is
an internal feature input, not a restored-image output or a claim that the
preview becomes a faithful clean photograph. No clipping or new exposure
normalization is added. After learning it can affect ADC-only inputs too;
all noise conditions therefore remain in the quality gate.

When enabled, autograd traverses the encoder to reach the input adapter. The
pretrained encoder parameters remain frozen and in eval mode. There is one
DINO pass at inference; training additionally computes the input gradient.
The native CFA path, physical FP32 operations, output representation, losses
and post-feature projection/gate are unchanged. Query/value LoRA stays disabled
in V56. Portable checkpoints include every input-adapter tensor; missing learned
tensors fail loading rather than silently resetting the branch.

## Actual validation

The complete CUDA-enabled suite passes **483 tests in 47.39 s**. Targeted tests
cover identity/common tensors/global RNG, rectangular padding, gradients through
the frozen encoder, compatibility with LoRA, nonzero portable reload and missing
weight rejection. A four-update CPU fixture resumes the complete model/EMA/
AdamW/RNG exactly with learned input weights. This is a small restart fixture,
not proof of bitwise deterministic CUDA optimization.

Genuine V43 step 2,000 EMA initializes both full-model preflight arms. All four
CFAs and mixed zero/positive shot/read priors give exactly equal initial FP32,
BF16 and FP16 outputs. An actual batch of 16 native 256px Commons training
patches also gives exact initial FP16 equality. Two discarded BF16 updates per
arm use identical observations. The input head receives gradients immediately;
earlier convolutions receive nonzero gradients on update two. Frozen DINO
tensors remain exact, and learned portable FP16 reload is exact. Peak CUDA
allocation was 6.845 GB for control and 7.331 GB for the adapted arm in this
preflight, not an isolated memory/throughput benchmark or a quality result.

## Controlled trial

[V56](../configs/dino-input-adapter-b16-v56.yaml) changes only the adapter flag
against immutable V54 step 1,000: same V43 EMA, fresh AdamW/EMA, seed 52,
batch 16, LR 3e-5, 100 warmup updates and 4,000 planned updates. The first gate
is at 1,000. Reviewed paired83/native128/Commons40170, domain proportions,
pre-downsample geometry and original validation remain fixed. The paired
corpus stays opt-in after its [full-schedule review](paired-expansion-v53-v54-4k-review.md).
No weak-source change is included. All 41 logged observation hashes must match
the control before numerical, analytic/flat, native and full GFX review.

The [actual launch receipt](results/dino-input-v56-launch.json) records frozen
source `4bf85a2`, controller identity, first update and matching observations
through step 125. Training is live; the receipt is a launch observation, not
a trained-quality result. The controller recomputes both models and baselines
and verifies full RGB16 outputs after the first gate.

The recent [structural-guidance JDD paper](https://arxiv.org/abs/2608.09995)
uses frozen DINOv3 and adaptation after patch tokens; it does not supply this
input adapter or evidence for its quality. This is an independent extension.
