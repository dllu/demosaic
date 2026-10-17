# Current RAW-head training batch sweep

A throughput sweep is queued for the current joint RAW-kernel model. There are
**no GPU measurements from this sweep yet**. Batch 16 remains unchanged in
production. The [earlier sweep](current-pipeline-batch-sweep.md) measured the RGB
restoration architecture; its numbers do not establish the best batch for this
RAW head. [Frozen plan, CPU checks and launch receipt](results/raw-kernel-training-batch-sweep-queue.json).

The queue waits for the original V67 10,000-update training run, its complete
serial evaluations, and the exact bounded CUDA inference-profiler process to
succeed and exit. It then uses that frozen final EMA checkpoint as the common
initializer for fresh, discarded timing cases. The model, four data manifests,
seed 50, LR1e-4, warmup 100, planned 10,000 horizon, native 256 patches, BF16,
workers 4+2+2, data fractions, geometry, palette and noise recipe stay fixed.
Each case starts at update 1 with fresh AdamW/EMA.

The [runner](../scripts/benchmark_raw_kernel_training.py) measures batches
4/8/16/32/48/64 twice in a deterministic shuffled order. Each case excludes 15
warmup updates and measures 45, including selected-domain loading/augmentation,
physical degradation, frozen DINO, forward/backward, AdamW and EMA. It excludes
initialization, warmup, monitor validation, final checkpoint serialization and
state auditing. Logging occurs every step with observation hashing disabled in
all cases. Timing uses differences between cumulative training times and records
the measured domain counts. CUDA allocation is the whole-case peak reported by
the trainer; it is not total unified system RAM.

Available memory must exceed
`1.2 × 21.34 GB × batch / 16 + 4 GB + 24 GB reserve` before a case starts.
The 21.34 GB reference comes from genuine current-model CUDA training. Cases that
fail this conservative estimate are explicitly skipped. The worker also caps
PyTorch's CUDA caching allocator at the smaller of available memory minus 24 GB
and 75% of CUDA-visible memory. This does not cap other processes or all other
allocations. Each owned case has a 1,200-second limit; failure stops the sweep
without an automatic retry. Large batches may be skipped, including when the
formula exceeds total physical memory.

Every case checks that all 94 initial restoration tensors equal the frozen EMA,
all 92 trainable tensors/32,931,920 parameters are active, actual DINO state stays
unchanged and gradient-free, and the final 94 model/94 EMA/92 Adam states are
finite with fresh optimizer step 60. Initializer, source, data and runtime config
hashes are retained. These checks occur outside the measured window.

The actual CPU check completed native 64/FP32 cases at batches 1 and 2, seven
discarded updates each with two warmup/five measured. Both used the reviewed
real V67 step 2000 EMA, original 10,000 schedule and all three domains. Independent
artifact replay checked checkpoints, source/data/log hashes, normalization
buffers, warmup LRs and timing arithmetic using Decimal. CUDA stayed
uninitialized. Actual negative checks rejected the pending exact profiler owner
before sweep output and skipped a memory-starved CUDA case without starting a
worker. These are engineering checks, not GPU timing measurements.

Review patches/s, two-run spread, memory and domain counts before choosing a
batch for a future quality experiment. Different batches process different
numbers of examples per update. This short sweep cannot establish convergence,
a unique hardware optimum or improved image quality, and does not automatically
change production batch size or LR.
