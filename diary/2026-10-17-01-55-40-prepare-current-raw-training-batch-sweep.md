# Prepare the current RAW-head training batch sweep

The earlier batch 16 choice was measured on the RGB restoration model. The
current phase-conditioned RAW-kernel model needs a separate experiment. Added
`scripts/benchmark_raw_kernel_training.py` without changing model/trainer/data
source or any production recipe. It preserves the original 10,000 horizon,
LR/warmup/seed/model/four manifests/fractions/noise/geometry/palette/precision
and workers, initializes every case from the same final 10,000 EMA, then discards
short fresh-optimizer updates. Measures batches 4/8/16/32/48/64 twice, 15 warmup
plus 45 measured, with deterministic shuffled order. Memory screening uses the
real 21.34 GB/B16 fixture peak, 20% margin, 4 GB scratch and 24 GB reserve. CUDA allocator
cap and 1,200-second own-case limit are additional bounds, not whole-system OOM
guarantees. Explicit skips, no automatic retry or production batch/LR change.

Actual CPU preflight at
`/mnt/external/demosaic/benchmarks/raw-kernel-training-sweep-CPU-preflight-v1`
completed native 64/B1+B2/FP32/workers 0, seven discarded updates each from the
real reviewed V67 first 2k EMA. Both exercised Commons/procedural, paired RAW and
native synthetic RAW, with finite 94 model/94 EMA/92 Adam states, all 92 trainable tensors,
32,931,920 trainable parameters, all 94 initial EMA tensors exact, normalization
buffers unchanged and actual DINO frozen/hash unchanged/no gradients. CUDA
stayed uninitialized. Independent replay verified source/data/checkpoint/log/
config hashes, warmup LRs and Decimal timing arithmetic. The actual pending
profiler gate rejected before output; forced low memory skipped the real CUDA
configuration without starting a worker. Ruff passes.

The immutable background queue waits for the exact inference-profiler owner,
which follows the original 10,000 training and full primary/statistical/artifact/
highlight chain. Frozen plan, source, actual CPU receipt and launch proof are
in `docs/results/raw-kernel-training-batch-sweep-queue.json`. The live waiting
controller has no children or sweep output. Its 74 file guards bind source,
data, recipe and checks. Model source is unchanged; the benchmark source-bundle
SHA differs only because monitor validation YAML is omitted consistently from
all timing cases. No final-model quality or new GPU timing result is inferred.
