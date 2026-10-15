# Full corpus, real night crops, and dark-field curriculum

Full 8×8 linear-light preparation completed: 44732 accepted licensed sources,
40170 train / 2306 validation / 2256 test. The license filter omitted 875 records;
14 failed decoding/preparation. The immutable snapshot is
`/mnt/external/demosaic/commons-v1/commons-44732.jsonl`, SHA-256
`8d7eeb6acabe2cacb007932b77b19f50659d50473d2041d89172043bec855d96`.

The complete dihedral fingerprint/correlation audit excluded three training-linked
protected images and one with insufficient fingerprint contrast. Counts are
40170 train / 2303 validation / 2255 test / 4 excluded. This remains conservative
duplicate screening, not proof against all scene/viewpoint overlap. Summary,
license counts, hashes and excluded IDs are in `docs/results/commons-44732.json`;
the full attribution manifest and audit remain local. Current runs retain their
frozen audited 24k subset. The common 8k/24k validation intersection contains all
427 earlier validation photos and no excluded sources.

V4 reached 12000 steps with balanced 16-photo panel rendered PSNR 30.5683 dB
and SSIM 0.89145, versus 29.9458/0.86353 at step 1000. These are training-monitor
scores, not a full-set or test result. The 100k-step run continues.

Checked native recent GFX100S RAW crops: ISO3200 night street signs/pavement
and ISO100 streetcar windows/overhead wires. Their September capture dates
postdate the local August Commons download snapshot. Personal files were read
only and remain local. Corrected crops and exact checkpoint hashes are in
`/mnt/external/demosaic/evaluation/recent-raw-crops-v4-corrected/`.
RawNIND still suppresses noise much more strongly on the night scene. The
single-image noise fit correctly refused this scene: accepted flats had only
0.0348 normalized intensity span, insufficient under the estimator's declared
threshold. No rejected estimate was applied.

A constant-field diagnostic confirms a bias/noise failure instead of relying
only on photographic averages. Checked 128/256/512 sizes; it persists at the
actual training/inference tile sizes. Added `scripts/probe_noise_response.py`
with frozen weights, fixed physical observations, explicit border exclusion,
camera bias and retained-noise measurements. These fields cannot measure detail
preservation and do not replace photographic evaluation.

Added optional `flat_fraction`, default zero, for float32 smooth neutral/color
fields and gentle ramps across twelve stops of illumination. Default draws were
compared with the archived V4 loader and are bitwise identical on 32 checked
indices. Validation still uses its real images. The V5 trial uses 10% smooth,
20% detailed procedural, 70% photographic draws, initialized from the frozen
V4 step-11000 EMA with a fresh optimizer. Its config schedules 30000 steps;
the initial invocation stops/saves at 5000 for review while V4 continues.

At the first V5 checkpoint, a 0.01-level, ISO1600-prior flat reduced absolute
camera bias from 5.95e-4 to 6.80e-5 versus its V4 initialization. Retained noise
sigma is still 0.692 of bilinear, versus RawNIND's 0.0356. This records an early
fine-tuning observation, not a matched ablation or final quality claim.
The 16-photo panel is 30.5564 dB/0.89030 at V5 step 1000. Full comparisons,
detail checks and more training remain necessary.

One 512×768 native validation crop checked full-frame versus tiled V4 inference:
rendered PSNR 28.8870 full-frame, 28.8826 with 256/64 tiles, 28.8869 with 512/64.
Mean camera differences are 5.46e-4 and 2.10e-4 respectively. This single crop
does not prove seam freedom globally. The 512/128 case used identical actual
tile positions on this small crop and is not an independent overlap experiment.
Concurrent-training timing is unsuitable for the 100 MP speed gate.

Follow-up primary research inspected JD3Net (WACV workshop 2026), FFNet (2026),
and the accessible JDD-LI abstract. Missing model licenses/weights in inspected
repository trees are recorded in `docs/research.md`; no unlicensed code was
incorporated. Numerical benchmark records from the complete 20k comparison are
now retained compactly in `docs/results/paired-20k-v2.json`.

All 44 tests, lint and formatting pass, including deterministic restart and the
new smooth-scene validation isolation check. Starting afresh over an existing
run's checkpoints now fails explicitly to preserve prior training evidence.
