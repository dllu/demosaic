# Build anchored physical channels once

Physically anchored RGB models used to construct three full-resolution
log-noise channels and a21-channel condition tensor, then replace those three
channels with physical black/white/noise-family anchors in another full tensor.
The model now constructs the anchors directly in the original concatenation.
Unanchored models retain their original log-noise channels. Returned channel
order, physical normalization, model configuration and learned weights stay
the same.

CPU verification:

- **116 tests pass**, with one CUDA-only skip while CUDA is hidden. Feature
  outputs and input gradients match the preserved original function byte for
  byte across all four CFAs, mixed noise families, flat/negative inputs,
  normalization masks, supplied/computed RGB, autocast, and contiguous or
  channels-last layouts. Returned tensor strides match as well. Existing
  stabilized-model and normalization-augmentation integration tests also pass.
- Genuine V63 EMA weights produce identical **61,440 RGB values** on four
  cached GFX80×64 contexts at relative native ROI`[216,224,80,64]`. GFX is
  forward-only; no reference or photographic objective is loaded.
- Eval-mode autograd on four deterministic synthetic64×64 all-CFA fields
  gives identical output and all **89 trainable parameter gradients**,
  covering32,904,704 gradient elements. There is no optimizer or weight update.
  Model bytes and RNG remain unchanged.
- At native512/B4, an actual CPU ATen census counts two→one full condition
  concatenations and3,145,728→zero logarithm output elements. This removes one
  **84MiB concatenation output materialization** per batch. It is an operation
  census, not a GPU peak-memory or timing measurement.

[CPU model/gradient evidence](results/physical-feature-work-CPU-v3.json),
[serving-size operation census](results/physical-feature-work-serving-census-v1.json),
and [frozen CUDA queue](results/physical-feature-work-CUDA-queue-v1.json).

The original physical function is preserved in
`tests/fixtures/physical_features_before_elimination.py`; its AST matches the
actual archived module, SHA-256
`9018feb07b37c7f1431e9c23af85a049f83dee9ed70747b8681a4cb3e0f7035a`.
The V63 checkpoint remains
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
Both policies share the separately [verified inverse cleanup](vst-unused-inverse.md).
All four original/inverse/physical-policy GFX array files have identical SHA-256
`425cc15ec6282b5caed94f64387efaf3e43d4608710094a122495ef8dc17dcad`.

`scripts/probe_physical_feature_work_cpu.py` reproduces the CPU check with
`scripts/env.sh` loaded and CUDA hidden. The new CUDA component runner waits for
the exact earlier inverse-probe owner to finish successfully; that probe already
waits for training, full review and native packaging. It compares all six
returned fields, bytes and strides, at native64/512 and both memory formats,
using deterministic nonphotographic inputs, then alternates five timing samples
after warmup. No new CUDA result is available yet. This is not a full-model
throughput, training-convergence, quality or100MP speed result.

The live V88/V89 training and its queued quality evaluation continue using
their original frozen model package. No new learned model or promotion follows
from this cleanup; their complete quality/native review remains pending.
