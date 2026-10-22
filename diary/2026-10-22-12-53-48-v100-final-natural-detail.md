# V100 final endpoint adds modest natural-detail gains

Recorded: 2026-10-22T12:53:48-07:00 (America/Los_Angeles).

V100 finished its planned 10,000-update continuation from the original V84
final20k EMA. The source-frozen trainer verified finite model/EMA/optimizer
states, exact initialization and unchanged official DINO weights. Its worker
PID844831/create1792689873.11 exited successfully before the quick CPU
comparison began. The existing controller started V101 freshly from V84;
the broad evaluation and full-frame queues remain in place.

Final checkpoint:
`/mnt/external/demosaic/v84-curated-quality-20261022-v2/train/V100/last.pt`,
SHA256 `4b689fb187b13df72fbf79ebd46f98cf7361c3ca8a97fb1f7afee940b249ad3e`.
Used its final EMA, not a best/intermediate selection. Ran the unchanged
copied detail worker and v2 input plan against the same 12 cached observations
as V84/RawNIND. CPU FP32, model/input hashes unchanged, all predictions finite.
Report: `/mnt/external/demosaic/heldout-detail-20261022-v1/V100-final10000/report.json`.

Mean V100−V84 sRGB PSNR on the four selected 240-pixel interiors:

| Condition | V84 | V100 | Difference, dB |
| --- | ---: | ---: | ---: |
| ADC-only | 38.72994 | 38.80606 | +.07612 |
| ISO100 prior | 40.24362 | 40.30529 | +.06167 |
| ISO12800 prior | 33.40933 | 33.41616 | +.00683 |

All 12 PSNR cases improve. SSIM and gradient error improve in 11/12, chroma
error in 8/12; record the small tradeoffs rather than requiring all diagnostics
to win. Actually viewed all three expanded boards at original resolution:
60 native160 cells containing noisy/V100/V84/RawNIND/exactGT. V100 and V84
look close; the high-noise white-feather/canopy/fur smoothing is not visibly
resolved. This supplementary four-source/three-condition/RGGB result is not
a full427, real-camera or full-frame improvement claim.

Published 12 V100 source triplets, updated all three current boards and
`docs/results/heldout-detail-V100-final-v1.json`. Copied immutable V100-view
boards under `.cache/current-quality-20261022-v1/heldout-detail-v1/V100-boards/`
so subsequent gallery updates preserve this observation. Updated README,
current-model, quality-first-training and heldout-detail with the actual
current result/status. V84 remains the broad-evidence baseline while V100's
modest progress is already visible. V101 tests the additional reduced-blur,
contrast-attenuation, weak-texture and reviewed-ROI package.

Validation: 94 bound artifact references across both detail receipts, all60
native comparison-cell hashes, exact shared noisy/GT pixels and current links
passed. The four frozen source/input plan guards pass. V101's owned worker
PID1084785/create1792698707.31 and both downstream queue controllers are live.
