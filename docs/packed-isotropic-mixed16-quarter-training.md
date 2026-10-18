# Mixed16 continuation to160,000 examples

The isolated continuation is running after the
[complete32k-example quality review](packed-isotropic-mixed16-first32000-review.md).
V72 no-DINO runs first; V73 DINO follows serially after successful completion.
Neither model is promoted. This is a launch record, with no new quality result.

The [complete review queue](packed-isotropic-mixed16-quarter-review-queue.md)
now waits for the exact training owner to exit and both boundaries to pass.

[Observed startup, plan/checkpoint hashes, exact owners and checks](results/packed-isotropic-mixed16-quarter-launch-v1.json).
The live status is
`/mnt/external/demosaic/runs/packed-isotropic-mixed16-quarter-workflow-v1.json`.

Resume each preserved2k checkpoint with its current model, Adam, EMA and RNG
in a separate run directory. Stop at10,000 optimizer updates /40,000 original
B4 source groups /160,000 example draws. The original40,000-update /
640,000-example cosine horizon remains intact; this boundary is25% of that
horizon. It matches the older40k-B4 models' example budget. All2k archives and
logs remain unchanged.

The frozen production worker keeps gain32/residual÷32, IEEE FP32, four B4
forwards per optimizer update, LR2e−4,500-update warmup and adaptive EMA
capped at`.999**4`. Training retains the same Commons, native and paired
manifests. Additional downloads remain outside this experiment. GFX scene
siblings and protected-final captures remain excluded.

Actual CUDA startup checks verify all restored model tensors, Adam tensors
and parameter groups, and CPU/Python/CUDA global RNG before the first update.
EMA is compared with its parent before the first resumed EMA update. The next
16 actual256px training batches match the frozen source/noise fixtures exactly.
The first no-DINO arm passed all these checks. DINO must pass independently
when it starts; its startup has not yet been observed in this record.

The controller archives4k/6k/8k/10k states, checks finite final states and exact
portable FP32 EMA reload, and compares403 logged source/noise/LR/example rows
across the pair, including403 older RAW observations per arm. These completion
checks remain pending. An exited owner or elapsed time alone never authorizes
a restart. The controller stops on failure and does not extend beyond10k.

The [first no-DINO 4k archive CPU audit](results/mixed16-quarter-no-dino4k-state-CPU-v1.json)
passes at 64,000 examples while training continues. All 852 model tensors,
852 EMA tensors and 852 Adam states are finite. Every Adam counter is 4,000,
and LR is the original schedule's `0.00019653544138946785`. Portable CPU
loading reproduces every EMA tensor exactly. All 163 logged macro rows through
4k have the expected example counts/LRs and 163 matching older source/noise
observations. Both current and EMA tensor sets have changed since 2k. All
22 inputs/56 guards and the preserved 2k archive remain unchanged. This audit
checks saved state and portable EMA loading. The 10k boundaries, DINO
continuation and complete quality review remain pending.

The continuation driver and existing production mixed-loop integration checks
pass26 targeted tests; Ruff passes. The separate
[genuine-parent CPU restart preflight](mixed16-trained-state-restart-CPU.md)
also passes. A complete numerical and native visual review remains required,
including exact synthetic noisy/denoised/GT triplets and the cached GFX
sky/building/foliage/fence views with an accurately labeled ISO100 reference.
