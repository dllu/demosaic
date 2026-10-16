# Packed detail trials started

V40/V41 now run sequentially from immutable V34 EMA in the private
`.cache/packed-detail-worktree` checkout frozen at `d380028`. Both enable the
physical Wiener detail prior; phase adapter/head LR is 1× versus 10×. The
original 53 native captures, frozen Commons4 training, original8 validation,
paired data, seed47, batch16 and planned3000 schedule match V38. Each stops at
1000 updates. The six-source V39 native extension is absent.

Controller PID700393 started at 2026-10-16 05:19:02 UTC. At the first resumed
inspection V40 had reached step825 with finite loss and gradients. Source files
remain frozen while it runs. The controller archive is
`/mnt/external/demosaic/runs/packed-detail-v40-v41-workflow.py`, SHA256
`01269f8befc61bfdf7cddf6056bcd7f16eaf2cde131e604ff313a65097920109`.
Status is recorded alongside it in `packed-detail-v40-v41-workflow.json`.

The controller requires all41 logged V38/V40/V41 domain/observation hashes to
match. It then computes known/unseen real, full427 synthetic and full102MP GFX
results for the new models. Cached V34/V37/V38/RawNIND comparators are admitted
only after protocol/code identity and exact classical case parity checks.
Each new full-frame output must pass SHA/size, actual 16-bit RGB shape/dtype,
sRGB ICC and sampled-code checks. Native triplets remain required before any
performance report or promotion. No quality result is inferred from training
loss or the engineering smoke.

The final metadata optimization validates Bayer indices once and prepares
detail variance before the CNN, avoiding a second post-CNN host sync. All32
targeted old/new packed tests pass; the preceding full suite passed321. The
actual CUDA smoke resumed through step10, retaining both optimizer groups and
their10× LR ratio. Both implementation commits are pushed.

The Commons download remains active under the existing lock/PID3989567;
no second downloader was launched. Frozen experiments do not automatically
admit newly downloaded data.
