# V111 full weak-texture and flat-color CPU evaluation

Recorded: 2026-10-23T22:11:46-07:00 (America/Los_Angeles).

V111's original final20k EMA is now running the complete existing analytic
weak-texture/neutral-flat and color grids on CPU while V112 trains. This adds
448 texture/flat and1,176 color observations, retaining every new float output
and all112 original weak-input batches. CPU2/nice10/IEEE FP32, no CUDA,
optimizer, RAW decoding or new control-model inference beyond four parent
replays. The original matched queues remain unchanged.

Four actual V104 B1 contiguous CPU color outputs agree with the earlier B1
channels-last GPU outputs within7.75e-7 camera units and.001 DN16 mean-channel
bias. The cases include the original worst V104 ADC field; this is a checked-case
execution comparison rather than a claim of all-case equivalence.

The independent auditor uses direct orthogonal Fourier sums instead of Torch's
pseudoinverse for carriers, NumPy FFT for neutral flats and separate NumPy64
reductions for colors. Its arithmetic reproduces four actual saved V111 weak
cases to1.42e-14 and all four parent color cases exactly. The complete audit is
queued after the exact diagnostic worker exits successfully, with no automatic
retry. Native selections remain the original three weak/neutral views and
three prospective colors plus the original V104 worst ADC case1008.

[Immutable launch/source/plan/CPU-check evidence](../docs/results/v111-full-diagnostics-queued-v1.json).
No complete diagnostic results or actual native review are claimed at this
launch. V104 stays the broadly evaluated baseline and V112 retains its original
training budget. This early CPU review will expose any color-bias tradeoff in
V111's material gains before the full matched GPU reporting queue.

A bounded reconstruction-literature check found that the official
[MambaIRv2 denoising release](https://github.com/csguoh/MambaIR/releases) dates to
December2024. No verified MambaIRv3 release was found in this search. The
[2026 data-centric Restormer study](https://arxiv.org/abs/2604.11468) concerns
fixed-sigma Gaussian RGB denoising, with substantial data/schedule gains; its
reported score is not evidence for our physical Bayer restoration task.
The active controlled loss test and prepared Tiny/Small capacity experiment
remain the concrete quality work; no speculative backbone swap was launched.

The remote feature-branch tip remains4381fc23, already in main through12f0810.
Hot-pixel removal and linear DNG support are merged. Originals, source cache
pixels, prior receipts, all twelve pinned plans and the current selector retain
their bytes. Human-facing times use America/Los_Angeles.
