# Expanding the Commons archive

The archive downloader has completed the
[local-original reconciliation and bounded-resume plan](commons-archive-handoff.md).
After the separate 1,188-source local cache preparation completed, all 1,188
originals were reconciled into the archive with immutable attribution preserved.
The subsequent two-worker, .25 starts/second job stopped normally at its
**608 GiB reserve** on **2026-10-19 14:40:59 UTC**, after adding **4,557 originals /
31.0 GiB**. Both exact processes have exited with controller-recorded exit 0.
Every new original passes an independent size/SHA1 check; the 1,188 reconciled
index rows remain exact including attribution. Five new HTTP 404s remain recorded.
The archive now holds **178,117 downloaded originals / 754.7 GiB**, with 279,548
pending, 2,477 excluded and 81 failed entries.
[Final counts, metadata and byte-check receipt](results/commons-bounded-reserve-stop-20261019-v1.json).
The completed log is
`.cache/commons-archive-handoff-memory-recovery-20261019-v1/download.log`.
Keep the reserve available for data preparation, checkpoints and review exports.

The next [separate CPU preparation](commons-post4557-preparation.md) now converts
4,337 of those arrivals to quarantined4×/8× caches, reusing the existing originals
with a560GiB cache-preparation reserve. Its selection, actual fixture and live
owner are pinned. The downloader stays stopped; current model recipes stay fixed.

The [reviewed local extension](commons-local1188-reviewed.md) separately freezes
890 additional training sources at both scales, with unchanged evaluation
membership. The V86/V87 context comparison retains its original manifests.
The recovery followed [evaluation-snapshot consolidation](evaluation-snapshot-storage.md),
which reclaimed 168.82 GiB. Original failed memory-guard attempts remain recorded.

## Earlier archive run

The existing Quality Images archive at `/mnt/external/qi` resumed on
2026-10-15 at 23:44:50 UTC. At startup it contained 77,025 verified originals
(195.2 GiB), with 380,719 pending files (4.23 TiB). Discovery and attribution
enrichment were already complete, so this job runs only the download phase.

It stopped normally at2026-10-18 04:49:19UTC (Oct17 21:49:19Pacific) when
available space reached its512GiB reserve. The actual downloader process has
exited. This run added **95,347 files /512.5GiB** at an average2.7MiB/s.
At that earlier stop the archive contained **172,372 downloaded originals /707.7GiB**, with
285,298 pending,2,477 excluded and76 failed entries. It remains a partial
download. Keep the reserve available for current evaluation exports before
resuming; download completion does not admit sources into an active experiment.

After that normal stop, [owned completed-evaluation checkpoint copies](results/completed-evaluation-snapshot-storage-v1.json)
were deduplicated without changing any bytes/paths/hashes, reclaiming7.12GiB
and leaving about519GiB free for pending review exports. Originals, model
archives and active evaluation files were untouched. The downloader remains
stopped rather than immediately consuming that export headroom.

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
PYTHONPATH="$PWD/../pupphoto" uv run --no-sync python -P ../pupphoto/download_quality_images.py status \
  --root /mnt/external/qi
```

After a clean stop, resume with `bash scripts/resume_commons_qi.sh`; use `nohup`
and redirect output to keep it independent of a terminal. `QI_RESERVE_GIB`,
`QI_WORKERS`, `QI_REQUESTS_PER_SECOND`, `QI_DOWNLOADER`, `QI_ROOT` and
`QI_LOG_FILE` override the defaults. The script refuses to start while another
copy holds its lock. To stop gracefully, send SIGTERM to the downloader Python
process; it records completed work and finishes active writes.

Downloading does **not** change an active training or evaluation manifest.

The [completed 16,231-source extension](commons-incoming-v3.md) provides a
separate reviewed corpus of 66,934 training images at both 8× and 4×. Current
models retain their original manifests. The [next 10,024-source snapshot](commons-incoming-v4.md)
is preparing with two CPU workers. It excludes all previous candidates and
recorded failures, then runs protected-scene and duplicate screening before
review. Neither downloads nor this preprocessing change training membership.

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

The original extension used this CLI with the previous frozen manifest, download
start time and a new output directory. For subsequent arrivals, follow the
[current selection procedure](commons-incoming-v4.md), which additionally excludes
all previous candidate/error sets and screens cached protected scenes:

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

`scripts/rebin_commons_extension.py prepare` prepared only the **1,808
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

The owned detached workflow waited on the base-freezer process before the
second command. Its final path is
`/mnt/external/demosaic/commons-extension-20261016-bin4-v1/audit/manifest.jsonl`;
this combined corpus is **complete and frozen**. Current trials do not use partial data.
Eleven new preparation/merge tests pass; the full suite passes **271 tests in
40.91s**, with Ruff passing. [The matched data/augmentation recipes](training-pipeline.md#matched-corpus-and-augmentation-pilot)
keep validation on the original 8× selection.

Four actual new-source precision checks compare unaugmented 4×→2× averaging
against their independently prepared direct 8× caches: maximum difference is
one uint16 code. This checks cache precision before geometry, not trained-model
quality. [Selection, code hashes and precision checks](results/commons-augmentation-pilot-startup.json).

## Preparation workers

A matched 48-source preparation sweep measures two shuffled repeats at 2/4/8
workers, using warmed originals and fresh output directories. Timing includes
decode/ICC conversion, linear binning, cache writing/checksums and publication;
child import/startup is excluded. The existing two-worker full preparation stays
live throughout. All 48 cache hashes match across all six cases.

| Workers | Mean images/s | Two-run range | Peak process RSS GiB |
| ---: | ---: | ---: | ---: |
| 2 | 4.19 | 4.18–4.19 | .93 |
| 4 | 7.56 | 7.48–7.64 | 1.23 |
| 8 | **12.20** | 12.10–12.29 | 1.83 |

This is about 2.91× preprocessing throughput on this small shared-machine sample,
not a training-speed gain or a complete-corpus timing claim.
[Full preparation sweep receipt](results/commons4-preparation-workers-v1.json).

At 2026-10-16 02:27 UTC, the owned full preparation resumed with eight workers,
reusing **26,314 published caches**. The frozen source selection/recipe is
unchanged. Existing caches are header/checksum verified and reused; original
photos are not decoded again for them. The old temporary ledger was archived
before restart. The first handoff attempt returned before the freezer reached
its stopped state and safely restored it; the corrected controller waits for
that state before replacing the producer.

Current log: `.cache/prepare-commons-bin4-full-workers8.log`; controller PID:
`.cache/resume-prepare-workers8.pid`; state:
`/mnt/external/demosaic/audits/commons-bin4-workers8-resume-v2/status.json`.
The controller keeps the original freeze waiter stopped while the new producer
runs, then resumes it in cleanup. The existing extension waiter follows that
same process. Both complete source memberships still pass their normal freeze
checks; no partial output enters training. The queued V34/V36 workflow waits for
both audited manifests and the current GPU review before starting.


Both complete4× manifests froze on2026-10-16 at02:53UTC. The base contains
40,170 train/2,303 val/2,255 test; the extension contains41,978 train with the
same val/test membership. Base SHA256:
`22d07361d1b67de077560f6b8571388db699ead2d164201c71fe71ec5755f4c3`.
Expanded SHA256:
`475052a7a63eefa7db785023a2b5fe9d4a69e99062dee9e5258c95364cf2bcfc`.
All1,808 new caches completed with zero failures, and the full base completed
with zero failures. The freeze waiter resumed and both exact-membership checks
passed; every expanded4× cache header was checked against its metadata.
[Complete freeze/selection/controller receipts](results/commons-four-complete.json).
V34 now trains on the complete base4× manifest; V36 follows on the complete
extension. Neither uses producer temporaries. The remaining18,414 uncached
sources plus revalidation/publication took26m06s after the eight-worker resume.


Status at2026-10-16 03:10UTC: V34 completed first1000 updates; V36 is training.
Both will receive matched development and full427/full-frame GFX reviews.
