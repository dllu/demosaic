# Probe compiled neural blocks on real CPU inputs

Previous goal turn made progress by preparing and checking final V67 report
assembly. Revalidated all seven live workflow owners by PID/creation/state;
only original training has children. New Commons8 producer remains live with
zero recorded errors; no job was duplicated or restarted.

The saved V37 GPU trace has 4,155 activities: 4,095 kernels, 48 copies, 12 memsets.
A read-only parser joins CPU operators by External id, separately checks runtime
correlation, and assigns innermost named ranges exclusively. Independent replay
matches all launch/kernel flow coordinates and the original RGB_CNN table.
External id differs from runtime correlation in 4,154 cases, so confusing them
would misattribute work. Legacy RGB_CNN sums 440.049904 ms over three instrumented
forwards; adds/ReLU/copies sum 220.857583 ms (50.19%). This is motivation for a
candidate, not proof of the current V67 GPU bottleneck. V67's saved CPU trace
has no GPU events. Source and summaries are archived under
`/mnt/external/demosaic/benchmarks/raw-kernel-inference-trace-analysis-v1/`.

Executed `.cache/probe_compiled_rgb_blocks_cpu.py`, archived under
`/mnt/external/demosaic/benchmarks/raw-kernel-compiled-blocks-CPU-probe-v1/`.
Actual reviewed V67 first 2k weights, CPU/native256/B1/FP32/two threads/nice5,
CUDA hidden; compilation limited to one compiler worker and 900 seconds.
Seven pure neural blocks compile through in-place nn.Module.compile with
Inductor/fullgraph/static shapes. Physical head/final skip/normalization/GAT/
RAW reconstruction and actual DINO stay eager at original precision. All seven
graphs and 128 generated CPU kernels execute. No source/config/model weights/
production defaults or training job changes.

Both fixed synthetic-photo inputs and four top-left256 GFX subcontexts produce
byte-identical eager/compiled F32 arrays, with repeat compiled outputs exact.
Independent NumPy/fileSHA and Python64 maximum/RMS replay checks all 1,179,648
scalars and twelve array files; all differences are zero, within the predeclared
1e-5 maximum tolerance. Entire model/actual DINO state and Torch RNG unchanged;
state hash and sky prediction also match the independently retained genuine
CPU profiler load/forward. CUDA remains uninitialized. Ruff passes. The receipt
is `docs/results/raw-kernel-compiled-blocks-CPU-probe.json`.

This is a real compilation feasibility/numerical probe, not a CPU or GPU speed
benchmark, trained improvement, global numerical-equivalence proof or quality
promotion. No new GPU experiment is queued yet. First inspect actual final 10,000
CUDA attribution; if it supports this candidate, prepare a bounded same-weights/
precision/input CUDA comparison after existing owned batch-sweep owner exits.
Full metric/native/100MP validation remains necessary for an inference option.
