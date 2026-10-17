# Resume original4k normalization schedules after first1k quality review

Pushed the completed first1k report/all81 native crops as50dbd9d. The explicit
mixed-quality decision completes the original4k horizon without promotion or
new data/training budget. Prepared separate run dirs with only recipe run path
changed, preserving all original1k logs/checkpoints/review. Original frozen
training package/source, seed50/B16/256/BF16/workers4+2+2, data/normalization
policies and4k LR curve remain exact. New logs start with an exact1k prefix.

The first production wrapper missed its __main__ guard for spawn workers. Worker
bootstrap failed, main stalled, and no training row beyond1000 or new checkpoint
was written in either arm. After checking PID/creation/cmdline/process group,
SIGTERM stopped only owned trainer group622244/1792260453.59. The original
controller recorded failure. Preserve v1 failure/status/logs/run dirs. A prior
inspection printed an erroneous 'gone' label because its broad exception also
covered a raced descendant query; explicit direct PID/creation/status checks
showed both owners live. Never infer owner death from a failed child listing.

Fresh v2 wraps runtime in main; actual frozen __mp_main__ import on CPU starts
no training/writes/CUDA. Actual control resumed, passed step1025 with finite
loss/grad and original LR. Read-only production hooks verify exact restoration
of model/all89 Adam states and all three RNG families before first fetch; EMA
is checked before its first EMA update, after the first optimizer step. Frozen
DINO hash matches370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd.
No discarded fixture updates. Augmented arm is serially pending.183 frozen
guards include completed1k evidence and preserved failed attempt. The final
boundary checks require finite91/91/89, complete RNG/source/data/parent/recipe,
original162 logged rows/LRs/masks and identical observation fingerprints across
both arms, then freeze step4000 checkpoints. No automatic promotion/continuation.

Actual controller622973/1792260581.40; child623004/1792260584.48.
Status: /mnt/external/demosaic/runs/normalization-v68-v69-original4k-continuation-v2.json.
Root: /mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-continuation-v2/.
Public actual launch: docs/results/normalization-original4k-continuation-launch.json.
Actual status is mutable; public capture points to an immutable snapshot.
Full4k quality/native review is not yet queued and remains required work.

Commons downloader continues:76,197 additional files/388.6GiB at11:09:53local,
692.9GiB free with512GiB reserve. No duplicate downloader or active corpus
substitution. Full PROMPT SOTA/decisive real-photo superiority/100MP10s objective
remains unmet/unproven.
