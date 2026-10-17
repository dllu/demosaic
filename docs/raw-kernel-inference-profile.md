# Attribute the current RAW-kernel inference cost

The retained V67 step-2,000 full-frame measurement takes **52.042 seconds** for
101.996 MP: compute/transfer accounts for 51.694 seconds and CPU blending for
0.245 seconds. This is the existing shared-machine measurement, excluding RAW
decode and TIFF encode. The 10-second goal remains unmet.

A bounded profiler now waits behind the final training, primary, statistics/hue,
artifact and supplementary GFX jobs. It will measure the genuine completed
step-10,000 model on the four retained native GFX contexts. The next optimization
should follow that attribution. No implementation or precision change is enabled.

[Executed CPU check, original timing and actual waiting-owner receipt](results/raw-kernel-inference-profile-queue.json).
[Profiler](../scripts/profile_raw_kernel_inference.py).

## Measurements prepared

The CUDA probe uses native 512-pixel inputs, batch 4, channels-last FP16 neural
compute with the existing physical FP32 guards. It retains the model, weights,
noise, WB, matrix and input arrays. Three warmups precede five synchronized
unhooked forward samples, five samples with branch hooks and one operator trace.
There is no full-frame rerun or throughput/batch sweep.

Five observational ranges cover the restoration trunk, DINO context, its nested
backbone, the RAW head and its nested coefficient convolution. CUDA events measure
inclusive intervals on the current stream. Parent and child intervals overlap;
they must not be added together. The separate operator trace records CPU/device
costs and allocations without shape/stack tracing, which can add overhead and
retain tensors. This follows the installed PyTorch 2.14 APIs:
[profiler](https://docs.pytorch.org/docs/2.14/profiler.html) and
[CUDA events](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.Event.html).

The coefficient convolution produces 324 FP32 channels. Its actual CPU test
output is `[1,324,256,256]`, or 84,934,656 logical bytes. Shape arithmetic predicts
1,358,954,496 bytes for one `[4,324,512,512]` tensor. This makes coefficient
materialization a useful profiling candidate; it does not establish a GPU
bottleneck or speedup. Physical filtering and clean-constant invariants remain
unchanged.

Every sampled and traced output must match the unhooked reference bit for bit.
The full model state hash, including the actual DINO backbone, and CPU/CUDA RNG
must remain unchanged. A genuine CUDA trace with positive-duration device events
is required; CPU fallback cannot produce a successful GPU result. The profiler
stores its trace, operator statistics, branch shapes and a reference float array.

## Executed CPU check and pending CUDA job

The final profiler source passed a real-model CPU preflight using the reviewed
V67 step-2,000 checkpoint and a native 256-pixel subregion of the first retained
GFX context, batch 1/FP32/two threads. All five hooks fire twice during sampling
and once during the operator trace. Hooked, unhooked and traced outputs match
exactly. Model/DINO state and CPU RNG stay unchanged. Named trace ranges and the
finite `[1,3,256,256]` reference array independently verify. CUDA remains
uninitialized; no GPU timing or GPU RNG check is claimed by this CPU execution.
Ruff lint and formatting pass.

The queued controller is PID 3021201 / creation 1792224684.54. Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-inference-profile-workflow-v1.json`.
Its exact predecessor is the supplementary CPU owner PID 3008664, verified live
and child-free. The new owner is also verified live and child-free, all 50 guards
verify and output is absent. An actual pending-predecessor call rejects before
output. The future completed gate and CUDA measurements remain unexecuted.

After successful predecessor exit, the controller checks its completed report,
audit and actual step-10,000 checkpoint identity. The profiler requires at least
32 GB available RAM and is limited to 300 seconds; a timeout stops only its own
child. Other projects' processes are untouched. Shared GPU use can still affect
timings. Operator allocations cover the traced call, while peak CUDA allocation
has its own scope; neither is total system RAM.

These samples exclude input/output transfers, tiling/blending, decoding and
encoding. They cannot establish a new 100 MP speed, quality improvement or
promotion. Full final native quality review remains required before selecting a
model; any later optimization needs its own numerical and quality checks.
