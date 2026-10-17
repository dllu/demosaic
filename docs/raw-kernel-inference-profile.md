# Attribute the current RAW-kernel inference cost

The genuine final V67 step10000 CUDA profile is **complete**. Median unhooked
forward time is366.464ms for the fixed four native512 GFX contexts. Inclusive
CUDA medians are180.088ms restoration trunk,138.932ms RAW head and30.048ms DINO
context; nested coefficient/backbone medians are30.831/23.001ms. Do not sum
parents and children. All hooked/unhooked/traced predictions match exactly;
model/DINO state and CPU/CUDA RNG remain unchanged.

[Executed profile, diagnosed failure/fix and new owned queues](results/raw-kernel-inference-profile-recovery-v2.json).
All1,209 kernel/copy/memset activities independently match both CPU external-ID
and runtime correlation associations. The instrumented trunk accounts for
181.055ms summed activity, with92.617ms (51.15%) in add/ReLU/copy. This supports
the bounded compiled-block experiment; it does not predict its speedup.

The first CUDA profiler failed **before warmup/timing**: its observational tensor
hash reinterpreted channels-last1×1 weights as bytes, but singleton dimensions
can report contiguous while retaining last stride21/67/etc. Hashing now copies
logical values to a canonical vector, preserving exact dtype bits and shape.
Eleven focused regression tests pass. An actual full-model CPU check reproduces
14 offending tensors, preserves the previous canonical hash across NCHW and
channels-last, and keeps the real256px prediction bitwise identical. No model
numerical computation changed. Failed v1 sources/logs/status remain intact;
the diagnosed recovery uses separate v2 directories and new exact owners.

The v2 profiler and child have exited successfully. The RAW batch sweep is now
running under PID3171937/creation1792232391.49; the conditional compiled follower
is PID3174750/1792232630.49. Their status paths use suffixes
`training-sweep-workflow-v2.json` and `compiled-probe-workflow-v2.json` under
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-`.
Verify actual PID/creation/status before acting. The
[completed quality review](raw-kernel-phase-joint-v67-full10k-review.md) does not
promote V67 and records52.704s full-frame restoration/blending. These resident
input profile samples exclude transfers/tiling/blending/decode/encode and are
not a new full-frame timing result. The sections below preserve earlier
preparation and CPU evidence; their v1 waiting status is historical.

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

## Neural block compilation candidate

A saved-trace reader now joins GPU activity to CPU operators by `External id`,
and independently cross-checks runtime `correlation` and launch/kernel flow
coordinates. This follows [Kineto's linked-activity serialization](https://github.com/pytorch/kineto/blob/main/libkineto/src/output_json.cpp).
All 4,155 activities in the retained V37 GPU trace match both associations.
Its RGB CNN accounts for 440.049904 ms across three instrumented forwards;
adds, ReLU and copies account for 220.857583 ms, or 50.19% of that range.
These are historical V37 trace sums, not the current RAW-model bottleneck,
critical-path timings or a new full-frame result. Inclusive nested annotations
are kept separate from the exclusive totals, avoiding duplicate attribution.
The actual V67 CPU trace has no GPU activity and supplies only operator counts.

This motivates a process-local experiment using
[Module.compile](https://docs.pytorch.org/docs/2.14/generated/torch.nn.Module.html#torch.nn.Module.compile)
on seven pure neural blocks: `m_down1/2/3`, `m_body`, and `m_up3/2/1`.
The actual reviewed V67 step2000 checkpoint ran through Inductor with
`fullgraph=True`, `dynamic=False`, CPU/native256/B1/FP32 and two threads.
Seven graphs and 128 generated CPU kernels executed. The physical head, final
skip, normalization, GAT, RAW reconstruction and DINO remain eager at their
original precision. No source, weight, configuration or production default
changes.

[Executed probe and independent array checks](results/raw-kernel-compiled-blocks-CPU-probe.json)
verify all six outputs are bitwise equal to eager: two fixed synthetic-photo
inputs and the top-left256 subcontext of each of four saved GFX observations.
All 1,179,648 FP32 scalars and twelve array files match. The complete model/DINO
state hash and Torch RNG remain unchanged; the sky array also matches the
separately retained profiler forward. These subcontexts are engineering inputs,
not replacements for the four standing native GFX review crops. No camera RAW
was decoded for this experiment.

CPU compilation and numerical agreement do not establish CUDA speed or
numerical equivalence. Read the queued actual 10,000 CUDA attribution first.
A [conditional bounded CUDA comparison](raw-kernel-compiled-CUDA-trial.md) now
waits after the existing owned batch sweep. It reads the actual current trace
before deciding whether to run, retaining the original weights, precision,
inputs and physical path. Its real-runner CPU switching/reference check passes;
CUDA remains unexecuted. Any promising change still needs numerical, native
quality and full-frame validation before becoming an inference option.
