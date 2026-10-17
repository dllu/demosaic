# Prepare current-model inference attribution

The previous goal turn made progress by adding, auditing, viewing and publishing
eight native supplementary GFX sign/platform comparisons, plus the queued final
checkpoint follower. Current exact process inspection confirms the original
training and all waiting review owners remain live. No restart or source/data/
schedule change was needed. Quality and 10-second goals remain unmet.

Inspected the actual retained V67 first2k full-frame timing:52.04187s total,
51.69413s compute/transfer and .24478s blending. Historical V60 timing differs
in model/history/shared load, so it is not a causal head-cost comparison. The
next speed action is current-model attribution of the compute/transfer interval.

Added a bounded profiler on the four fixed GFX packed contexts, with5 observational
module ranges: DINO context/backbone, restoration trunk, RAW head/coefficient
convolution. Native512/B4/FP16-neural/physicalFP32,3 warmups,5 unhooked and5 hooked
samples,1 operator trace. Inclusive nested ranges are labeled; no parent+child
summation. CPU/device/allocations and shape metadata are separate from unhooked
timings. Positive genuine CUDA trace events are required, with no silent CPU
fallback. No compiler, precision, weight, model, input, tile or noise change.

Final-source real2k CPU preflight v2 passes B1/native256/FP32 on an actual retained
GFX subregion: all5 hooks sample twice/trace once, outputs bitwise unchanged,
whole model/actual DINO state and CPU RNG unchanged, CUDA uninitialized. Named
trace ranges and finite saved F32 reference independently verify. The first
execution also passed; v2 follows lint-only context-manager cleanup. Both are
retained. Profiler source matches the executed v2 archive; lint/format pass.
The CPU run contains no CUDA timing or CUDA RNG evidence.

Coefficient output is actually324 FP32 channels,84,934,656 bytes atB1/native256.
The B4/native512 shape predicts1,358,954,496 bytes for one coefficient tensor;
this is resource arithmetic, not an observed GPU bottleneck or optimization gain.

Launched waiting controller PID3021201/creation1792224684.54 behind exact
supplementary CPU owner3008664. Both verified live/child-free, output absent,
50 immutable guards. Actual pending owner rejection passes before output. Future
completed parent/CUDA branch remains unexecuted. The controller checks genuine
final10000 checkpoint/report/audit identity, available RAM>32GB and a300second
owned-child timeout, touching no other processes. Final quality/native review,
actual CUDA bottleneck interpretation and any optimization remain future work.
No protected-final score, new training budget or promotion.

[Documentation and primary API sources](../docs/raw-kernel-inference-profile.md).
[Executed evidence and actual queued-owner receipt](../docs/results/raw-kernel-inference-profile-queue.json).
