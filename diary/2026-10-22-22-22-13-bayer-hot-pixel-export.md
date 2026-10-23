# Repair isolated Bayer hot pixels before DNG restoration

Recorded: 2026-10-22T22:22:13-07:00 (America/Los_Angeles).

Added the explicit `--hot-pixels` option to the [DNG exporter](../docs/dng-export.md).
It repairs the normalized Bayer input before restoration, so the correction is
present in the stored DNG rather than only a preview. Darktable's existing
hot-pixel module skips RGB linear DNGs. Existing model weights, training and
comparison defaults remain unchanged.

The detector requires a site to exceed all eight same-phase neighbors by a
six-sigma noise margin and a factor of two, with minimum excess .005. A nearby
site that rises above its own phase median by three sigma protects coherent
light detail. Isolated candidates use the same-phase neighbor median. All
decisions read unchanged input; strips do not cascade. Three-pixel borders,
clusters and supported lights are left alone. Unresolved single-color lights
remain ambiguous without a measured defect map.

The four private GFX100S inputs produce 2,574 / 767 / 3,229 / 1,001 corrections
in capture order, with 1,242 / 980 other candidates protected in the two ISO6400
frames. These counts are detections, not independently verified physical defect
counts. V101 final10000 EMA, the prior ISO noise coefficients, IEEE FP32,
tile512/overlap64/B4 and native11662×8746 geometry are retained. Initial native
triplets show the isolated bright specks disappearing; the inspected illuminated
façade control retains its visible pattern. There is no exact GT, new training,
population-quality score or speed claim. Private before/after crops, coordinate
maps and receipts stay with the requested exports, preserving the earlier
manifest separately.

All28 focused tests pass: four CFA phases, sparse changes and unchanged input,
representative Poisson/read noise, threshold validation, line/edge/small-light
protection, strip invariance, independent DNG decoding, and a complete CPU
RAW/DNG/JPEG export with an injected hot pixel. Ruff and whitespace checks pass.
The feature lives on `feat/linear-dng-export` in an isolated temporary worktree;
the concurrent main checkout and source photo directories are left untouched.
