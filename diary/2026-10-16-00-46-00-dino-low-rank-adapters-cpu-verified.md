# Add optional DINO low-rank adaptation and verify CPU execution

The current full-resolution model keeps foundation features frozen. To test
whether adapting those features to noisy RAW previews helps quality, implement
opt-in rank4 query/value updates in every pinned DINOv3-S attention block. This
adds73,728 trainable parameters, retaining all original foundation tensors.
Rank0 is the default and retains the previous path. No private running source
is changed.

The implementation uses PyTorch parametrizations, zero initial B and unit
alpha/rank scale. Shared adapter modules are also registered outside the
excluded `context.backbone` checkpoint namespace. This ensures portable
checkpoints retain the learned updates; optimizer traversal deduplicates their
parameter objects. Autograd traverses the backbone only when adapters are on.
Original foundation parameters remain frozen and the backbone remains in eval.

Nine dedicated CPU tests pass in7.77s, covering initial equality, gradients to
both factors, original-weight preservation, invalid layouts/ranks, nonzero
portable checkpoint loading, missing-learned-tensor rejection and exact
interrupted/resumed model/EMA/AdamW/RNG equivalence. The complete CPU suite before
adding the final resume test passed343 with8 CUDA tests skipped in37.42s.
Ruff passes. The fresh V44/V45 initializer preflight was rerun with the new
default-rank0 implementation: all66 common tensors and initial all-CFA outputs
remain exact, retaining the original common tensor digest.

A separate genuine pinned DINOv3 CPU fixture loads V43's existing projection/
gate. All24 target projections and73,728 parameters verify. Frozen/rank4 initial
predictions match exactly; B receives finite nonzero gradients. After one
synthetic-only adapter update, original foundation tensors remain byte-identical
and saved/restored context predictions match exactly. The actual executed
method source, fixture, script and validation logs are archived under
`/mnt/external/demosaic/benchmarks/dino-lora-cpu-preflight-v1/`.

[Architecture, sources and remaining gates](../docs/dino-low-rank-adaptation.md),
[genuine execution receipt](../docs/results/dino-lora-cpu-preflight-v1.json).
LoRA is an existing adaptation method; its language-model paper does not prove
RAW quality. This implementation and these checks are not a trained improvement.

V37/V39 have completed the step2000 continuation, V43 is finishing its own
continuation, and controller PID1038531 remains live. Queue PID1048124 waits for
its complete review and process exit before the current-pipeline batch sweep.
Do not overlap GPU checks or training with either workflow. Next: publish the
corpus review; inspect the sweep; complete GPU/precision/backward/full-checkpoint
tests for adapters, then run matched quality experiments. Native report triplets
and accurate GFX labels remain required before promotion. Full objective unmet.
