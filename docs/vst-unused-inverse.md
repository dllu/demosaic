# Remove unused inverse-transform arithmetic

The table inverse in `GeneralizedAnscombe.inverse` computed the closed-form
approximation, including three reciprocal terms, then discarded it. Compute
that approximation only in the closed-form branch. The algebraic and table
branches retain their original returned expressions.

This is an inference/training implementation cleanup, with no new weights,
loss, noise model or quality claim. The active V88/V89 experiment and its
evaluation continue to use the original archived model package, including
`vst.py` SHA-256
`355124a374177f1c08271834149c5979ab3477fdf255c60aa7cee0d47792a76b`.

CPU verification:

- **58 passed, one CUDA-only test skipped** with CUDA hidden. Across inverse
  modes, noise profiles and dtypes, compare output and input-gradient bytes
  against a fixture containing the original function. Include negative values,
  table anchors and their immediate neighbors, tails and noncontiguous inputs.
- The genuine V63 checkpoint produced identical output bytes for **61,440 RGB
  values** across the four cached GFX contexts. Each context uses an 80×64 native
  crop at relative `(216,224)`; weights and RNG remain unchanged. This is a CPU
  implementation-parity probe, without GT scoring or a new visual-quality claim.
- A CPU ATen dispatch census for 15,360 values decreases from **56 to 39**
  dispatches; cubed elements decrease from 15,360 to zero. These are neither GPU
  kernel counts nor speed measurements.

The [CPU model-parity receipt](results/vst-unused-inverse-CPU-v1.json) records
the checkpoint, source, cached observations and output hashes.
`scripts/probe_vst_unused_inverse_cpu.py` reproduces that probe;
`tests/fixtures/vst_inverse_before_elimination.py` preserves the original method.

An isolated CUDA parity/gradient/timing probe is deferred until the exact
training, quality-review, closure, reference and report-package owners finish.
It measures only the inverse component at native 64 and 512 pixels, with four
noise profiles and alternating measurement order. It cannot establish a
full-model or full-frame speedup. No CUDA timing result is available yet.

The probe is queued at
`/mnt/external/demosaic/experiments/vst-unused-inverse-CUDA-v2/plan.json`,
SHA-256 `c8de5a6abfc923fbb1f42da870ee69f672d58795b19cbdfbf84f047be2f74f1a`.
It reuses the unchanged candidate snapshot from the first probe queue, whose
idle owner was explicitly cancelled when reconnecting evaluation to the
[corrected completion coordinator](spectral-log-completion.md).
