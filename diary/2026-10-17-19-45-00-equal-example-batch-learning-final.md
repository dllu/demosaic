# Completed equal-example batch4/batch16 learning comparison

All four CUDA arms completed4096 identical ordered example draws. The exact
GPU owner exited. Independent replay verifies2560 finite ordered training
records,96 domain means, all86 inputs/guards and the per-arm1792/1024/1280
Commons/native/paired example totals. All852 Adam states per arm are finite at
1024 B4 or256 B16 updates. Fixture fingerprints stay unchanged; weights discarded.

Final scaled-residual B4 loss/MSE ratios are Commons.90274/.74728,
native.96677/.98862 and paired.99206/.99911. Scaled B16 gives
.89912/.73664,.96850/.94912 and.98869/.99962. Its Commons/native MSE is
1.4%/4.0% lower than scaled B4, with essentially unchanged paired MSE. Native
original loss is slightly worse. Raw B16 alone gives mixed results. The midpoint
favored B4 on Commons, emphasizing the need to complete the fixed horizon.

This is single-seed repeated-training-set evidence, not photographic quality,
convergence or throughput. It warrants a full-data mixed effective-batch trial.
Current production B16 batches select one domain per optimizer step, while the
probe mixes four scheduled B4 groups. Next implement grouped updates while
preserving original source indices, per-group supervision and degradation RNG;
compare physical batch16 against accumulated B4 for execution speed. Preserve
default training/resume behavior and record microbatch/example/update counts.
Then train/review a real fresh checkpoint with the selected execution strategy.

The original launch evidence stays immutable. No production batch change,
new quality model, protected-final scoring or SOTA claim is made here.
