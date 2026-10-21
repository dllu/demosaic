# Complete the V93 control and begin larger-corpus V94 training

Recorded: 2026-10-21T00:46:26-07:00 (America/Los_Angeles).

The original V93 worker PID2430283/create1792558558.82 completed its full
20,000-update control stage and exited successfully. It executed 20,000 training
forwards, 160 validation forwards and 20,160 DINO calls. Its final EMA container
is `/mnt/external/demosaic/v43-curated-training-20261020-v1/train/V93/last.pt`,
SHA256 `7a5f091b17b64a44611bd2dad53d7ec8ecd0f76ef48463f74b61b576a0b43182`.
The completed worker receipt is
`3827a8f3e20e90e96748682e754282c64d3f5fc4af2341c95e7623014742987a`.
The original controller PID2355916/create1792554876.82 remains live.

Added `scripts/audit_v43_quality_training.py`, an independent CPU-only auditor
for these completed matched arms. Its actual V93 integration passes. It
verifies all four 4k/8k/12k/16k diagnostic checkpoints, final 20k and separate
validation-best: hashes, canonical original V43 configuration/tensor keys,
71 finite model/71 EMA tensors and 69 Adam states with the right per-file counter,
original step2000 initializer, curated/native/paired/validation/protocol
identities, source hash and frozen-input guards. Final and validation-best are
both at20k for this run; final EMA remains the predefined primary endpoint.

All 801 scheduled training metric rows, step1 then every25, have finite recorded
losses and gradient norms. All five validations complete eight sources under
seven conditions/four CFAs,28 cells/224 observations each, with finite present
metrics. All first24 production input hashes exactly match V93's discarded
CUDA preflight; the probe's checkpoint was never used as the initializer.
The executed worker additionally verifies unchanged frozen DINO/no gradients
at completion. The auditor performs no inference or extra training and does
not initialize CUDA. It retains an exact executed-source snapshot with its
receipt. Ruff checks and formatting pass. Independent audit receipt:
`a334c90c491ea1a5a5ed50275a969c6a78a2e6951ba3142ea2af59ae82e814dd`.

The same controller advanced serially to the larger V94 arm after the stable
headroom wait. Actual worker PID2579665/create1792568448.55 is live on the
88,484-source curated cohort. Its immutable startup observation records
production through logged step625 with finite recorded losses/gradients;
the original V43 initialization assertion passed before its first forward.
V94 otherwise preserves V93's architecture, schedule and augmentation. V95's
blur-free/more-low-contrast treatment follows V94. Startup observation receipt:
`a24733ef7f782176c5aaecba3958d36717cefb08eb8cf06cb15cbb2de13b49d9`.

[Published completed-control evidence](../docs/results/v43-quality-V93-completed-training-v1.json)
records the actual completed arm and early V94 observation. Updated the quality,
validation, experiment and completion guides. The fixed427-photo, known/unseen,
weak-detail/color and GFX comparisons still require all three completed20k
endpoints and actual native crop review. Training-validation subset means are
not substituted for that comparison. V43 remains the working reference; no
quality gain, promotion or inference-speed result is claimed.

