# Complete matched Tiny Small training and start endpoint evaluation

Recorded: 2026-10-24T16:29:27-07:00 (America/Los_Angeles).

V115 fitted Small completed its original20,000-update continuation at16:24 PDT.
V114 Tiny had already completed the same budget at11:12. Both original workers
and the training controller have exited successfully. The automatic evaluator
has started the full photographic panel under its original PID/creation identity
and frozen source. No training or evaluation was restarted.

Each endpoint has20,000 model/encoder training forwards,20,000 AdamW updates and
640 model/encoder validation forwards. All801 logged training input/domain/LR
rows match between Tiny and Small, along with all20 validation comparator scores
and panel definitions. Unlogged production input tensors are not independently
verified. The original source archive remains
`cd35f14079462639b0fac6d9b20052b8bba395a396bcaa668383bd6575569f92`.

The Small final checkpoint SHA256 is
`fee5d05c599cb32f5a1e587c31979f040a06152c8e14676481eee83a4ce04d84`.
A separate CPU-only payload inspection directly reopens it: all91 model and91
EMA tensors are finite FP32, all89 Adam states are finite and at step20,000,
and the official Small revision/configuration and fitted parent match. The
original worker verifies its frozen Small encoder hash/no gradients and all91
initial EMA tensors against the explicit fitted initializer. Verification adds
zero neural/encoder calls, optimizer updates, noise draws, RAW decoding or CUDA.
Prior Tiny evidence is reused, preserving its generic Small status-text typo.

Updated README and current training/model/data/research/evaluation guides to show
both completed endpoints and active quality evaluation. This establishes the
trained artifacts and successful handoff; endpoint quality is still unmeasured.
V112 remains the learned baseline, with its separately measured eight-view
option. No new full-quality point is added to the version plot yet.

The original evaluator retains the declared full photo/camera/analytic panels,
six standing GFX contexts and full102MP exports. Its independent CPU audit will
reuse exact saved predictions/targets and prepare native triplets. Actual native
and GFX viewing follows; useful measured gains can update the current guides
without an old promotion gate. V116 continues to wait on that exact audit before
its own CUDA checks and original20k data comparison. Its sources and all other
waiting owners remain unchanged.

[Completed endpoint proof and live handoff](../docs/results/v114-v115-trained-quality-running-v1.json) ·
[Current matched training guide](../docs/small-aligned-training.md).
