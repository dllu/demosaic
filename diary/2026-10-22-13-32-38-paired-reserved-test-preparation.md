# Prepare the untouched paired-RAW test reserve

Recorded: 2026-10-22T13:32:38-07:00 (America/Los_Angeles).

The previous turn made concrete progress with V101 clean-target/sampling
inspection (13d97ab) and started the full V84/V100 CPU real-camera comparison.
This turn revalidated that exact evaluator owner PID1143331/create1792700264.56
and the live V101/controller/evaluation/full-frame owners. No run was restarted.

Research notes already cover several recent joint/RAW references. The larger
real-camera evidence gap was the acquired but unprepared 16-scene publisher
test reserve. Prepared it without loading a model, scoring it or viewing test
images, using the existing frozen numerical implementation and unchanged
development defaults:512px/3×3 grid/128px integer-registration search, green-L1
limit.035, calibrated AHD auxiliary reference and measured-CFA primary masks.

All57 metadata-selected source RAWs remain byte-exact. Their16 scene names are
disjoint from both development panels and paired training32, and their RAW
SHA256s are absent from the active native/paired manifests. This is exact-ID/
scene screening, not a complete alias or near-scene-independence claim. The
publisher labels six scenes as unknown-sensor. No source HDD was read.

All16 scenes/32 noisy captures/288 fixed-grid crops prepared successfully with
zero registration/coverage rejections. Twenty-three captures use the existing
input-only Haar estimate; nine use the disclosed nominal ISO fallback. The
prepared files occupy about2.39GiB. Every crop's hash, shape, dtype, finite
values, sensor-count bounds, source/reference membership and exact reference
mask were checked. Valid coverage ranges .91058349609375–1.0. Source/input
guards pass after both preparation and full array validation. CUDA was never
initialized, and targets remain outside model selection.

Prepared manifest:
`/mnt/external/demosaic/evaluation/paired-reserved-test-prepared-20261022-v1/manifest.json`,
SHA256 `9962ca5f7ecdad38480e52cbb41b8c0c1792d11379e3f73dcd2760253dbf608e`.
Private plan/caller/result/288-file validation:
`.cache/current-quality-20261022-v1/reserved-test-preparation-v1/`.
Published `docs/paired-reserved-test.md` and
`docs/results/paired-reserved-test-preparation-v1.json`, linked from evaluation,
docs/index and current requirements. This is preparation-only readiness, not a
quality result or reproduction of the publisher's complete exposure benchmark.
The existing subset uses metadata-selected ISO-near1600/highest-at-most12800.

The ongoing CPU comparison completed all72 known-camera crops/8 pairs/4 scenes.
V100 measured-CFA mean54.17845 versus V84 54.17122: +.00723dB, with a scene
interval crossing zero. Their completed native crops look close. The five-scene
unseen CPU panel is still running; its result will be reported on completion.
