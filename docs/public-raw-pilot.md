# Public low-ISO RAW candidates

Nine camera samples from [raw.pixls.us](https://raw.pixls.us/) are acquired and
decoded into **quarantine**, not training. Each selected catalog entry explicitly
links CC0, and all nine published SHA256 values and HTTP byte counts verified:
909,367,652 bytes total. The acquisition archives the catalog, selection, EXIF,
implementation and per-file license/source records.
[Acquisition receipt](results/public-raw-pilot-acquisition.json).

The site requests low-ISO scenery and releases new submissions under CC0, but
individual files still need inspection. Its catalog includes other licenses;
the downloader refuses entries without an explicit CC0 link. Seven acquisition
tests check the license/metadata/catalog identities before network I/O, verified
reuse, standing capture identifiers and competing ownership. Existing checksum
verification is reused from the paired RAW downloader.

All nine decode as ordinary 2×2 Bayer with actual ISO 50–100. The same tested
phase-aligned binning used for native RawNIND targets creates 4× and 8× uint16
camera-RGB caches, with no demosaicer, WB, matrix, tone curve or 8-bit intermediate
in those target caches. These are **low-noise estimates, not exact noiseless GT**.
Per-cache shapes, hashes, raw metadata and code counts are retained;
having many uint16 codes does not establish independent sensor precision.
[Quarantine/cache receipt](results/public-raw-pilot-quarantine.json).

| File ID | Actual camera | ISO | CFA | Content review |
| ---: | --- | ---: | --- | --- |
| 2788 | Nikon Z7 | 64 | RGGB | Color chart/shallow focus; omit from proposed photographic subset |
| 2979 | GFX50R | 100 | RGGB | Ferry Building and bay |
| 3204 | Leica Q2 | 100 | GBRG | Ferry/river |
| 3478 | Sony a7RIV | 50 | RGGB | Valley/foliage |
| 3652 | Panasonic S1R | 100 | GBRG | Hills/foliage |
| 4213 | Nikon Z7II | 100 | RGGB | Building/grass/sky |
| 4493 | GFX100S | 100 | RGGB | Trees/grass/sky |
| 6231 | Sony a7RV | 100 | RGGB | Trees/grass/buildings |
| 7872 | Leica SL2 | 100 | GBRG | Brick/window/foliage |

Dataset inspection overview, **resized**, fixed ×1 metadata-WB/color rendering.
This is not a performance report or a native-pixel comparison. Sources are CC0;
the preview applies phase binning, color rendering, orientation and resizing.

![Public RAW source inspection overview](images/public-raw-pilot-overview.png)

No exact source matches were found against 211 previously acquired training,
development, protected-final and standing-GFX capture hashes. Actual metadata
also rejects the standing GFX date/file family. A cross-render near-duplicate
screen checks all 46,738 Commons records and 53 native training references using
dihedral dHash ≤24, correlation ≥.97 and aspect tolerance 3%. The wider thresholds
flag possible RAW/JPEG overlaps for review. No candidates were flagged. The
reviewed overviews show no standing train/platform scene.
[Screen and limitations](results/public-raw-pilot-screen.json).

This does not prove full scene separation: crops, tone curves and different
views can evade fingerprints. Official-final captures were checked by exact
source identity only; no new model or final performance scoring occurred.
Further admission work is required. Every new row and the top-level manifest
remain `split: quarantine`, which the training loader rejects. Neither these
samples nor their rendered screening caches enter V32/V34/V35/V36.

To reproduce acquisition in a new directory:

```bash
source scripts/env.sh
uv run --no-sync python scripts/fetch_public_raw.py \
  --survey docs/results/public-raw-candidate-survey.json \
  --catalog /mnt/external/demosaic/references/raw-pixls/catalog.json \
  --output /mnt/external/demosaic/references/raw-pixls-pilot-next --workers 2
```

The downloader preserves verified existing files, uses at most two workers and
a 512 GiB free-space reserve, and publishes the complete acquisition manifest only
after every checksum passes. Interrupted files are retried; finished files are
reused. A new recipe requires a new output. The current phase-bin prototype and
its exact source are archived in `/mnt/external/demosaic/raw-pixls-quarantine-v1/source/`.
