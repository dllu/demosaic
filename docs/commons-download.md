# Expanding the Commons archive

The existing Quality Images archive at `/mnt/external/qi` resumed on
2026-10-15 at 23:44:50 UTC. At startup it contained 77,025 verified originals
(195.2 GiB), with 380,719 pending files (4.23 TiB). Discovery and attribution
enrichment were already complete, so this job runs only the download phase.

The detached job uses the existing `pupphoto/download_quality_images.py`,
three workers, at most 0.5 request starts/second, and a **512 GiB free-space
reserve**. The downloader accounts for in-flight files before admitting work,
resumes partial downloads, and verifies size/SHA-1 before publishing originals.
The reserve leaves room for prepared data, model checkpoints and evaluations;
the complete pending archive exceeds the SSD's current free capacity.

Operational files:

- Log: `/mnt/external/demosaic/downloads/commons-qi-resume.log`
- Startup receipt, source hash and baseline database counts:
  `/mnt/external/demosaic/downloads/commons-qi-resume-receipt.json`
- Launcher PID: `.cache/commons-qi-download.pid`
- Cooperative single-job lock: `.cache/commons-qi-download.lock`

Inspect progress without starting another job:

```bash
tail -20 /mnt/external/demosaic/downloads/commons-qi-resume.log
source scripts/env.sh
uv run --no-sync python ../pupphoto/download_quality_images.py status \
  --root /mnt/external/qi
```

After a clean stop, resume with `bash scripts/resume_commons_qi.sh`; use `nohup`
and redirect output to keep it independent of a terminal. `QI_RESERVE_GIB`,
`QI_WORKERS`, `QI_REQUESTS_PER_SECOND`, `QI_DOWNLOADER`, `QI_ROOT` and
`QI_LOG_FILE` override the defaults. The script refuses to start while another
copy holds its lock. To stop gracefully, send SIGTERM to the downloader Python
process; it records completed work and finishes active writes.

Downloading does **not** change an active training or evaluation manifest.
V32/V33 and the V34 augmentation recipe retain the frozen 44,732-source selection.
Existing validation/test membership and the excluded GFX scene/siblings remain
fixed.

## First prepared extension

`scripts/expand_commons.py` selected 2,006 newly downloaded licensed sources at
least 2048px per side, prepared linear-light 8×8 uint16 caches, and screened their
fingerprints against every existing source. The frozen result contains
**41,978 train/2,303 validation/2,255 test/196 reserved/6 excluded** records:
**1,808 additional training images**, 196 new reserved sources and two new
near-duplicate exclusions. All 44,732 original records remain field-for-field
identical, including every validation/test source. The active models have not
switched to this extension.

Manifest:
`/mnt/external/demosaic/commons-extension-20261016-v1/audit/manifest.jsonl`

SHA256: `38ac5fc61892ee31ddf841ad2b06ebf5ec68b6cb2196b4f7aa97b49775cbfb78`.
[Selection, implementation, screening and verification receipt](results/commons-extension-20261016-v1.json).

The selection is frozen before preparation and reads the live archive index
read-only. Existing prepared pixels are reused. First-seen caches are SHA256
verified; descriptors are cached by pixel-file hash and checked size/mtime.
Screening uses 256-bit dihedral dHash within 8 bits, aspect ratio within 3% and
normalized thumbnail correlation ≥ .99, with exact cache identity checks. Any new
cluster linked to an existing source is excluded. New-only duplicate groups
retain one member, preferring a reserved validation/test hash bucket. New
validation/test buckets stay **reserved**, outside active evaluation. This is
near-duplicate screening; arbitrary crops and different viewpoints can remain.

The standing RAWs/siblings are not ingestion inputs. A separate Commons
title/model/date metadata sanity check found no matching capture identifiers;
metadata can be missing and this is not visual scene recognition. No GFX pixels
are used to fit training transforms or select new training sources.

To prepare another separately versioned extension, pass the previous frozen
manifest as the base, the download start time and a new output directory:

```bash
source scripts/env.sh
uv run --no-sync python scripts/expand_commons.py \
  --base-manifest /path/to/previous/frozen/manifest.jsonl \
  --source /mnt/external/qi --since 2026-10-15T23:44:50+00:00 \
  --output /mnt/external/demosaic/commons-extension-next \
  --fingerprint-cache /mnt/external/demosaic/audits/commons-extension-fingerprints-v1.sqlite3 \
  --workers 2
```

The script refuses competing audits or replacement of a frozen output. Tests
cover protected split anchoring through new duplicate bridges, rotated matches,
reserved buckets, cache corruption and concurrent output ownership. Full suite:
**260 passed in 32.71s**; Ruff passed. A future 4× version must rebin the admitted
new sources and preserve this audit before testing the expanded corpus with
augmentation before the last reduction.

## Reuse the 4× base when extending the corpus

`scripts/rebin_commons_extension.py prepare` is now preparing only the **1,808
admitted new training sources** at 4×, with one worker. It does not decode or copy
the old corpus. Its archived implementation and frozen selection are under
`/mnt/external/demosaic/commons-extension-20261016-bin4-v1/`; progress is in
`.cache/prepare-extension-four.log`, launcher PID in `.cache/prepare-extension-four.pid`.

The separate `freeze` stage requires the complete frozen old 4× corpus and the
complete new preparation. It combines their absolute cache paths without copying
pixels. The expected result is 41,978 train / 2,303 validation / 2,255 test;
reserved/excluded sources are omitted and remain recorded in the audit. Every
active source/split and its attribution must match the audited 8× membership.
Cache shapes/dtypes are checked from actual NumPy headers. Producer checksums
are retained; the merge does not rehash all old pixels. The audit is published
before the final manifest, with a cooperative lock and no overwrite of frozen
output. Partial producers, wrong dimensions, changed splits/credits and duplicate
identities are rejected.

```bash
source scripts/env.sh
COMMONS_BASE=/mnt/external/demosaic/audits/commons-44732-v1/manifest.jsonl
COMMONS_EXT=/mnt/external/demosaic/commons-extension-20261016-v1/audit/manifest.jsonl
COMMONS_EXT4=/mnt/external/demosaic/commons-extension-20261016-bin4-v1
uv run --no-sync python scripts/rebin_commons_extension.py prepare \
  --base-manifest "$COMMONS_BASE" --expanded-manifest "$COMMONS_EXT" \
  --output "$COMMONS_EXT4" --workers 1
# Only after the full old4x freeze and new preparation finish:
uv run --no-sync python scripts/rebin_commons_extension.py freeze \
  --base-manifest "$COMMONS_BASE" --expanded-manifest "$COMMONS_EXT" \
  --base-rebinned-manifest /mnt/external/demosaic/audits/commons-bin4-frozen44732-v1/manifest.jsonl \
  --output "$COMMONS_EXT4"
```

An owned detached workflow waits on the live base-freezer process before the
second command. Its final path will be
`/mnt/external/demosaic/commons-extension-20261016-bin4-v1/audit/manifest.jsonl`;
this combined corpus is **not ready yet**. Current trials do not use partial data.
Eleven new preparation/merge tests pass; the full suite passes **271 tests in
40.91s**, with Ruff passing. [The matched data/augmentation recipes](training-pipeline.md#matched-corpus-and-augmentation-pilot)
keep validation on the original 8× selection.

Four actual new-source precision checks compare unaugmented 4×→2× averaging
against their independently prepared direct 8× caches: maximum difference is
one uint16 code. This checks cache precision before geometry, not trained-model
quality. [Selection, code hashes and precision checks](results/commons-augmentation-pilot-startup.json).
