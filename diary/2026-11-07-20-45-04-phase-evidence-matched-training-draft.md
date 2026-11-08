# Preserve warm-start clocks and prepare matched phase-evidence training

Recorded: 2026-11-07T20:45:04-08:00 (America/Los_Angeles).

The V178 matched trial is implemented and CPU drafted from the actual V172
checkpoint. Both arms preserve all 188 existing model tensors, 141 Adam states
at update 900 and the saved network EMA. The evidence adapter adds 3,120 zero
weights with no allocated Adam history and a zero EMA tensor. Optimizer payloads
are deep-copied so independently initialized CPU arms cannot share moments with
each other or the source checkpoint. Thirteen CPU AdamW/state tests pass,
including genuine restoration, distinct parameter clocks and invalid EMA
metadata rejecting before any parameter mutation.

Each arm will make one additional identical cached pass: 900 updates/3,600
images and 100 ADC skips. The network clocks finish at 1,800, the new adapter
at 900. The existing seven-term objective, domain weights and cached
scene/target/noise/parent rows are unchanged. This compares the evidence path
and its small extra capacity together; it is separate from V175's nine-pass
fresh-noise recipe. No new parent/DINO, sensor, geometry or original-photo work
is planned. Actual row-8 checkpoint/model/Adam/EMA/RNG restoration must resume
at row 9 without replaying a prefix. Both raw and EMA endpoints include the
adapter's corresponding state.

The actual frozen entry rejects missing admission before importing Torch, and
the actual training entry rejects a missing prepared plan before CUDA or a
training claim. These intentional CPU prerequisite checks are preserved and
are not failed GPU experiments. The draft verifies one actual V172 checkpoint
load, all old moments/weights/EMA exact in both arms, and CUDA uninitialized;
there are no actual matching, frozen, DINO or sampler forwards or updates.

Review implements all four endpoints on all 822 fixed inputs, retaining 36
native cases, with exact V169 replays, ADC identities and addition closure.
The renderer plans 48 boards and 24 native triplets with identical coordinates,
160×160 crop pixels and display transforms. Both protected GFX scenes, fine
cab windows, sky, building, foliage, coarse fence, stronger V161 detail and
periodic references remain visible. ISO100/AHD/JPEG references remain qualified
and unscored. A completed CPU layout fixture checks all 72 figures/24 triplets/
18 sheets and 16,588,800 displayed crop channels using only existing V172/V174
pixels. Every PNG header explicitly says fixture/no V178 quality. One fixture
triplet was viewed for layout only; no fixture is published as a model result.

A single CPU controller is live at PID 453410/create 1794113512.6, nice 10 on
CPUs 4/5, about 19 MiB RSS with no Torch/CUDA libraries loaded at inspection.
It waits for the actual admission watcher and successful result, inspects both
actual admission checkpoints and their 142 fresh Adam states/adapter/frozen
weights, then prepares and launches control, evidence, review and CPU rendering
once each. Failed scientific prefixes are preserved without automatic retry.
The controller stops for actual viewing; it cannot claim report/quality gains.
Its source, draft hash and launch identity are sealed. New trial artifacts use
local recovered space with a 2 GiB forecast, preserving existing reserves and
V175/admission allocations. No trial plan, GPU claim, scores or predictions
exists yet. V175 and its completion watcher retain their original owners/code.

V175's actual row-5,000 checkpoint passes a separate CPU audit: 3,600 new/4,500
total updates, all 141 Adam clocks at 4,500 and all 47 frozen tensors exact.
Four completed continuation passes cover 4,000 rows, 400 ADC skips, 3,588 fresh
batches, 12 retained noisy rows, 14,376 durable events and 3,600 bit-exact FP32
loss totals. Five visits to the same scene retain target/calibration/pairs but
have distinct actual sensor seeds and RAW/variance/parent fingerprints. The
audit uses immutable prefix byte hashes and does not regenerate noise or
inference. This is a running checkpoint/trace check, not final quality evidence.

All 97 current neural files, the original 96 V175 sources and 18 sealed V175
helpers remain exact. No original photos or unavailable source storage is
accessed. Model recommendations and existing real comparison crops remain
unchanged pending measured gains and actual native viewing.

[Matched training/review draft](../docs/phase-evidence-training.md) ·
[CPU draft, source and controller receipt](../docs/results/v178-matched-trial-CPU-draft-v1.json) ·
[Publication verification](../docs/results/v178-matched-trial-publication-verification-v1.json) ·
[V175 four-pass checkpoint/prefix audit](../docs/results/v175-four-pass-boundary-audit-v1.json).

