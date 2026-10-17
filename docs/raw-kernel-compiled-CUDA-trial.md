# Conditional neural-block compilation trial

An isolated v2 CUDA trial is queued after the exact running RAW batch-sweep
owner exits. The [actual final10000 CUDA profile](results/raw-kernel-inference-profile-recovery-v2.json)
now supports the prespecified triage: trunk/unhooked median ratio.49142,
add/ReLU/copy fraction.51154, all1,209 device activities independently mapped.
**No CUDA compilation or compiled timing has executed yet.** The original v1
chain exited after an observational hash-layout failure before profiling;
its artifacts remain intact. The v2 follower is PID3174750/creation1792232630.49,
status `/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-compiled-probe-workflow-v2.json`.
It waits for the exact v2 batch owner PID3171937/1792232391.49 and reads the
successful v2 profiler. Verify actual owners/status before acting. The
compiled runner and existing CPU switching fixture are unchanged; only its
observational helper now hashes channels-last singleton strides correctly,
with separate actual full-model hash/output identity checks. The earlier
[launch receipt and frozen plan](results/raw-kernel-compiled-CUDA-trial-queue.json)
include the executed CPU checks. The [six-input CPU experiment](raw-kernel-inference-profile.md#neural-block-compilation-candidate)
established local numerical agreement with the real reviewed step2000 weights.

Before using the GPU, the controller reads the completed final10000 CUDA profile
and its actual trace. Every GPU-to-CPU operator association must independently
match runtime correlation. The median restoration-trunk interval must account
for at least 20% of the unhooked median forward time, and adds/ReLU/copies must
account for at least 15% of the trunk's summed device activity. These are fixed
triage thresholds for one bounded experiment, not a speed prediction. Missing
correlations or inadequate activity produce a completed record without a trial.
Inclusive intervals and summed activity have different scopes; nested ranges
are not added twice.

If supported, the [runner](../scripts/probe_compiled_raw_kernel.py) loads the
genuine final10000 checkpoint and the same four native512 GFX contexts, with
batch4, FP16 neural compute and FP32 physical computation. Eager output must
match the saved prior-profiler reference exactly. Only `m_down1/2/3`, `m_body`
and `m_up3/2/1` compile through Inductor, fullgraph and static shapes. Physical
head, final skip, normalization, GAT, RAW reconstruction and DINO remain eager.
Model configuration, canonical model/DINO tensor state and checkpoint hash
must remain unchanged.

The compiled output must be finite and repeatable. Before timing, each image
must satisfy maximum absolute error at most 1e-5 and RMS at most 1e-6 in linear
camera units relative to eager. Failure saves the numerical results and skips
timing. Acceptance is an engineering bound, not an image-quality conclusion.

Timing uses ABBA/BAAB order: four blocks per policy, five forwards per block.
Three initial warmups and compilation are excluded, as is one policy-switch
warmup per block. Both CUDA events and synchronized wall time are retained.
Every completed block's final output must exactly match its policy reference;
measured forwards must preserve RNG. Both policies retain compiled-cache
allocations. These shared-machine resident-input samples exclude tiling,
transfers, decoding, blending and encoding; they cannot prove 100 MP speed.

The controller requires 40 GB available memory and limits its own child group
to 900 seconds. The child keeps a 24 GB reserve when setting the CUDA caching
allocator cap, also limited to 75% of visible CUDA memory, and uses one compiler
worker. These bounds do not cover other processes or every allocation. Failures
stop without automatic retry; other projects' processes are untouched.

The actual runner's CPU fixture loaded the prior genuine V67 step2000 profiler
observation at native256/B1/FP32. Seven graphs and 128 generated kernels
executed. Both eager and compiled policies, including switching and excluded
warmups, produced array files bitwise identical to the prior reference; model,
DINO and measured RNG checks passed. Independent replay verified the arrays and
timing bookkeeping. Its single block per policy is engineering evidence only.
Real pending batch-owner rejection occurred before trial output. Legacy V37
GPU data exercises triage arithmetic; actual V67 CPU-only data is rejected as
GPU evidence. The eventual completed10000 CUDA path remains unexecuted.

The waiting owner is PID3097416 / creation1792229124.07. Its status is
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-full10k-compiled-probe-workflow-v1.json`.
It has no child or trial output at launch. The preceding training/evaluation/
highlight/profile/batch jobs retain their existing order. This trial changes
no production defaults and makes no promotion decision. Any promising result
still needs independent numerical/timing checks, native quality review and
full-frame validation before becoming an inference option.
