# Continue the matched native-corpus comparison

The V43 first gate gives a small positive source-balanced gain over V37/V39,
but still does not establish convergence, broad superiority over RawNIND or the
requested qualitative margin. Continue all three matched arms from step1000 to
step2000 before deciding whether to complete the planned3000 schedule.

The controller is live at PID1038531. V37 has passed step1400, maintaining the
original decaying learning rate and using about7.2GB of GPU memory. Each arm
runs sequentially in its own original private worktree. Preflight checked every
Python module against its archived source, the complete checkpoint hash, step1000
on every saved AdamW parameter, RNG state and the planned3000 schedule. Existing
first-gate evaluation weights remain immutable. The optimizer is not reset.

The [launch receipt](../docs/results/native-corpus-2k-launch.json) records the
three source bundles, checkpoint/driver hashes and machine-readable plan.
The live workflow is
`/mnt/external/demosaic/runs/native-corpus-v37-v39-v43-2k-workflow.json`.
Its driver is archived beside it; per-arm training logs remain in the V43
private worktree's `.cache`. Source changes to those worktrees are excluded
while they run. No second owned GPU experiment overlaps this comparison.

The gate includes known/unseen paired development, the full427-photo plus16
procedural suite, and full102MP GFX inference. Shared Commons/paired input
observations must match across arms; comparator reuse requires exact evaluator
and classical-case parity. Publication will verify and include at least two
native exact-synthetic-GT triplets per new checkpoint, plus standing GFX foliage,
fence, sky and building crops with accurately labeled real references. The
existing V43 first1000 README alias stays fixed until a reviewed selection.

Commons downloads continue independently; newly downloaded sources are not
silently admitted into these frozen recipes. The original user requests for
augmentation before final binning, an empirical batch-size sweep and lazy domain
loading are already implemented and documented in the geometry/data reviews.

Next: review the completed second gate, including texture failure cases and
source-balanced uncertainty, before promoting a checkpoint. The SOTA, DINO
ablation and10-second goals remain open.
