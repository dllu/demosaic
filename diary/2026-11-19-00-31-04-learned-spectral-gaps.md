# Supervising wire gaps and checking Bayer phase

Recorded: 2026-11-19T00:31:04-08:00 (America/Los_Angeles).

## Matched gap training and Bayer phase checks

Trained the same directional spectral head on additional natural detail,
exact wire breaks and continuous low-amplitude controls. Three heads
tested ordinary training, exact spatial gap supervision and a gap correction
penalty. Two additional heads repeated the matched and exact-gap recipes
with disjoint nearby-green phase and center Bayer evidence.

Exact gap supervision cuts 14.73 DN16 of ISO6400 paired error inside true
breaks and loses 9.74 intact-response points versus matched training.
The Bayer phase checks lower absolute gap error by 0.37 DN16 at similar
added texture against the independently scaled matched control. The
held-out intact-response interval includes zero. All 16 standing boards,
four exact comparison boards and ten triplets were inspected. The real sky
stays smooth and the fine cab crossings remain incomplete. Initial review
schema and selection retries are preserved with their receipts.
[Report](../docs/learned-spectral-gaps.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

Both training runs, scoped scoring and native viewing are complete. These
crop studies add no comparable full-photo or measured-camera point to the
[PSNR history](../docs/performance-history.md).

## Large-corpus continuation

Local-only 20k verified 40,000 distinct photos, 40,000 noise seeds and
160,000 native queries. The arms match through 18k on 36,000 photos and
144,000 native queries each. The spatial arm continues toward 20k. A live queue waits for both milestones before running the
64-photo exact-target evaluation and both standing GFX scenes. The latest
completed matched quality review remains 15k.
[Execution status](../docs/scene-full-epoch.md#execution-status) ·
[Local coverage audit](../docs/results/scene-full-epoch-v1/local-020000-prefix.json) ·
[Matched review queue](../docs/results/scene-full-epoch-v1/queue-review-020000-launch.json).
