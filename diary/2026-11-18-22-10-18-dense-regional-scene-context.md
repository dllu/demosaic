# Replay dense regional context above the matched 12k checkpoint

Recorded: 2026-11-18T22:10:18-08:00 (America/Los_Angeles).

The matched spatial 12k EMA replays the same native Bayer queries with
six scene-preview policies. The registered hybrid holds the whole-scene
offset mean and blends its spatial variation halfway toward a dense
neighborhood. The pure whole-frame density and regional-only arms, a
resampled near view, and mirrored features exercise separate controls.
The registered hybrid lowers independent flat fine-band RMS by 0.118
DN16 on the 48 photos outside the pilot. Fine detail stays close to the
coarse preview and coupled fine-increment error rises 0.091 DN16. The
preset fainter half has no resolved fine change. Sixteen overlapping
ordinary preview predictions match the original 12k monitor exactly.

All eight native standing boards and sixteen fixed development boards
were viewed. The coarse fence remains visible, overcast sky stays smooth,
and the green cab crossings remain incomplete. The 3,072 full and
regional preview grids can sample the known carrier frequencies, while
none fits as a literal oscillation on the finest scene feature grid.
The targeted tests pass 44. This is a scoped replay with no additional
broad PSNR result.
[Report and crops](../docs/scene-regional-context.md) ·
[Main camera map](../docs/gfx-qualitative.md) ·
[Fine green fence map](../docs/gfx-green-mesh.md) ·
[Comparable model scores](../docs/performance-history.md).

The training traces match through 13,000 updates and 26,000 distinct
photos per arm. Local-only completes 15,000 on 30,000 photos and
120,000 native queries. The spatial worker continues toward that matched
checkpoint. The 15k evaluator is live and waiting. The 12k pair remains
the last fully reviewed model comparison.
[Execution status](../docs/scene-full-epoch.md#execution-status) ·
[15k review queue](../docs/results/scene-full-epoch-v1/queue-review-015000.json).
