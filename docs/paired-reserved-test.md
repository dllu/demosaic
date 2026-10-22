# Paired-RAW test reserve

The metadata-selected publisher test reserve is now prepared and validated:
**16 scenes, 32 noisy captures and 288 native 512-pixel crops**, from 57 cached RAWs.
Six scenes carry the publisher's unknown-sensor flag. No model has been run
or scored on these prepared targets, and no test images were visually viewed
during preparation. Keep this set outside model selection; the known4/unseen5
development panels continue to guide V84-based quality work.

[Preparation and full file/array validation](results/paired-reserved-test-preparation-v1.json).
There is no exact scene-name overlap with either development panel or paired
training set of 32 scenes. No selected RAW SHA256 occurs in active native/paired training
manifests. These checks do not establish complete alias or near-scene
independence. Source RAWs and training memberships remain unchanged.

## Fixed preparation

The existing [paired-RAW protocol](evaluation.md#paired-real-raw-evaluation-sources)
uses the development defaults: a 3×3 grid of 512-pixel crops, green-plane integer
registration within 128 pixels and one scalar exposure gain per clean/noisy
reference pair, shared across methods. Registration rejects green L1 above .035;
crop masks require at least 50% valid reference coverage. All 16 scenes/32 pairs/
288 crops pass without rejection. Actual valid coverage spans 91.06–100%.

Primary references contain measured low-ISO CFA samples after alignment/gain.
The auxiliary RGB is separately AHD-demosaiced and calibrated against its own
CFA; it is **not exact RGB GT**. Low-ISO references retain noise. Masks exclude
clipped/out-of-rendering-gamut reference regions using the existing rules.
Input-only Haar fits supply conditioning for 23 captures; 9 use the disclosed
nominal ISO fallback. These fits are not dedicated sensor calibration.

Every crop's SHA256, dimensions, dtype, finite values and exact reference-mask
construction were checked. Sensor-count bounds and reference membership pass.
Validation reads arrays without evaluating a model or choosing visual targets.
The source snapshot and all 57 original file hashes still match.

The acquired subset selects up to two clean frames per scene, noisy ISO
nearest 1600 plus the highest remaining ISO at most 12800, from metadata. It does
not reproduce the publisher's entire exposure set or published benchmark
protocol. Later quality reports must describe that scope.

## Local artifacts and reproduction

Acquisition: `/mnt/external/demosaic/references/rawnind-dataset/manifest-test.json`.
Prepared: `/mnt/external/demosaic/evaluation/paired-reserved-test-prepared-20261022-v1/manifest.json`,
SHA256 `9962ca5f7ecdad38480e52cbb41b8c0c1792d11379e3f73dcd2760253dbf608e`.
The prepared directory uses about 2.39 GiB, excluding its small source archive.
All reads used cached external SSD files; no source HDDs were needed.

After sourcing `scripts/env.sh`, reproduce into a fresh directory:

```bash
uv run --no-sync python scripts/prepare_paired_raw.py \
  /mnt/external/demosaic/references/rawnind-dataset/manifest-test.json \
  --output /mnt/external/demosaic/evaluation/paired-reserved-test-replay \
  --size 512 --grid 3
```

The completed job used the existing frozen numerical source from
`.cache/current-quality-20261022-v1/evaluation-queue-v1/work/`.
Its plan/caller/result and full 288-file validation inventory are in
`.cache/current-quality-20261022-v1/reserved-test-preparation-v1/`.
No test-scoring job is queued by this preparation.

Dataset: Benoit Brummer and Christophe De Vleeschouwer, Raw Natural Image Noise
Dataset (2025), [publisher release](https://doi.org/10.14428/DVN/DEQCIM),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0).
Cached `permissions.txt` retains individual scene credits and CC0 grants.
