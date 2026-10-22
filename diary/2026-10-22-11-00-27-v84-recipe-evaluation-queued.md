# Queue V84 recipe quality evaluation

Recorded: 2026-10-22T11:00:27-07:00 (America/Los_Angeles).

The preceding turn made concrete progress: V84 became the baseline, current
documentation and galleries were refreshed, and the V100/V101 continuations
were launched. Rechecked the exact controller/worker PIDs and creation times;
V100 remains live and the frozen training inputs are unchanged.

Added a source-frozen evaluation queue for both recipe continuations. It waits
for the exact original training controller and final worker to exit with both
10,000-update runs completed, then compares their final EMAs against V84 on
the existing full photographic, known/unseen measured-CFA, weak-detail, color,
GFX and GFX-highlight panels. Shared observations/display metadata and IEEE
FP32 computation are preserved. It uses cached GFX RAFs and prepared/cached
evaluation inputs, keeping originals read-only and avoiding source HDD access.
The existing evaluator now derives its method counts from the declared models
instead of assuming four ViT-S checkpoints. It also checks that native triplets
cover at least two source groups. All prior four-model workflows retain their
case counts.

An actual CPU176/B1 reporting smoke used V84 plus both discarded eight-update
CPU checkpoints, two photos, one procedural image, two noise conditions and
two CFAs. All 72 score rows completed; independent summary arithmetic matches
exactly. Each learned model performed 12 forwards, used the expected frozen
DINO identity, and preserved weights, config, parameter identities, global RNG
and sampled inputs. All six native160 triplets were viewed at original size
(18 panels), with noisy/GT pixels identical across models. This is engineering
evidence only. It says nothing about final V100/V101 quality or CUDA evaluation.

The focused ownership/resource/reporting checks passed: 66 tests. Production
queue controller PID899941/create1792692004.15 is live and waits on the original
training owner. No evaluation GPU worker is launched while training remains
active. Its plan is
`.cache/current-quality-20261022-v1/evaluation-queue-v1/plan.json`, SHA256
`83e737f85a2c6650697f521c46c9fcea58bd40f1086642face9847b1af82e6a8`.
Output namespace:
`/mnt/external/demosaic/v84-curated-evaluation-20261022-v1/`.

[Readiness evidence](../docs/results/v84-recipe-evaluation-readiness-v1.json)
binds the smoke, frozen queue and launch. Actual production images and metrics
will guide current recommendations, with visible strengths and adverse cases
reported directly rather than reinstating the old all-diagnostic promotion
barrier. The broader PROMPT quality goals remain open.
