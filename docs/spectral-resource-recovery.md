# Spectral trial: operational disk-reserve recovery

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

Control training has resumed from the verified1000 state. The published
observation reaches1050 and exactly reproduces the earlier recorded1025/1050
inputs, losses, gradient norms and LRs. The original4000 schedule remains fixed.
The [full final review is queued](spectral-review-preparation.md); model quality
and actual native viewing remain pending. V43 was the comparator during this study.

[Recovery evidence](results/spectral-resource-recovery-v2.json).
[Immutable operational addendum](spectral-root-reserve-addendum.md).

The previous controller stopped near logged update1750 with a generic resource/
runtime-bound error. Its active time was716 seconds, below its13,462-second
timeout. Root free space below the128GiB operational floor was directly observed
after exit, while RAM/external space were adequate. Exact resource values at
the old stop were not persisted, so this identifies the observed root-space
constraint without claiming a complete historical resource trace. Future stops
now record those values explicitly.

The new controller uses a64GiB root reserve. Heavy checkpoints/evaluation files
are already on the external SSD; its500GiB reserve and RAM/CUDA bounds remain.
The project cache contains114GiB of retained experiments, benchmarks and related
material; those artifacts are preserved. This is an operational reserve change,
without model/data/noise/loss/precision/seed/batch/schedule/quality-threshold changes.

Twelve resource/retention tests pass. The builder independently compares ASTs
for the training worker, retention helper and recipe preparer; all are identical
to the validated previous driver. All46 model modules remain byte-identical.
Only resource checks and failure-time resource logging change in the controller.
Existing genuine CPU/CUDA restart evidence therefore remains applicable to the
unchanged training code; no new training-quality claim follows.

The full saved1000 model/EMA/AdamW/RNG state is restored from SHA256
`2388c26b26767f0dd60c466b385bdaa93c7ca52543e1639310540898c184ab9c`.
Only the remaining3000 retained-trajectory updates are authorized. The control
timeout is12,746 seconds after deducting the failed worker's716 active seconds.
Unsaved work after1000 is discarded and may repeat, rather than being counted
as equal total hardware work. All30 recorded old post1000 steps are preserved
for exact source/loss/gradient replay checks at the final endpoint.

The new plan freezes296 files/804 inputs, SHA256
`68d190f70e14e19fe2765f034ec63b26cdb9ea3e09a38d69986854cb4618efe1`.
Current root:
`/mnt/external/demosaic/experiments/spectral-v88-v89-resource-recovery-v2/`.
Controller557934/1792464246.16 and worker558182/1792464315.65 are exact live
owners at observation. The fresh spectral arm stays queued in the same bounded
controller. Original plans, status/failure records, logs and checkpoint remain
intact. Inspect current handles/status before inferring later completion.
