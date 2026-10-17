# Check the retained24k RAW checkpoint during training

The previous goal turn made concrete progress: commit6226d99 added and queued
trained-checkpoint compilation with full RGB comparisons and repeated102MP
latency. The present turn verifies the exact live training/review/compilation
owners; it does not interpret an observation timeout or waiting status as a
stopped job. The original Commons downloader is also still alive.

An independent CPU-only audit of the retained no-DINO24k checkpoint now passes.
SHA256: `5cc735e14c155c46d24a3499fec6f4ce3a6352846602170ffa828c2515bcaf91`.
The model/EMA and852 Adam states are finite. Every Adam counter is24000,
moment shapes match parameters, and second moments are nonnegative. All852 raw
and EMA tensors differ from their own8k state. This rules out a completely frozen
restoration state across this interval; it does not demonstrate useful learning.

The original160k horizon, actual resumed recipe, seed/precision, four manifests
and their snapshots match. Independently reconstructing the complete source
snapshot yields50dc11ec5c906fbbc4d3c5b1b530b95acb3b40a5f725d3a622891b2471c21d16.
The saved962 training rows through24000 retain the original8k prefix, the special
8001 resumed row and every expected25-step row. All logged LRs match the original
schedule exactly. The audit's first attempt used a differently parenthesized
LR expression and failed on floating-point operation order; matching the actual
trainer expression resolves that audit error without changing training.

Private operator, fixed log prefix and receipt:
`/mnt/external/demosaic/benchmarks/packed-isotropic-no-dino-24000-state-CPU-v1/`.
Public receipt: `docs/results/packed-isotropic-no-dino24k-state-CPU-v1.json`.
No CUDA context, inference, optimization or new performance result. RNG encodings
are present; this audit does not restore CUDA RNG or independently regenerate
all logged observation fingerprints. Both full-state continuation and actual40k
quality/native review remain running or queued. No model is promoted, and the
PROMPT.md goal is not complete.
