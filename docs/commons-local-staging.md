# Bounded additional Commons originals on the local SSD

A separate background download stages **1,188 new originals**, with a16GiB
original-content budget and224GiB local free-space reserve, under
`.cache/commons-qi-local-20261018-v1/`. It uses two workers and at most.25 request
starts/second. This uses local headroom while the external archive is below its
512GiB download reserve. The active V82/V83 corpora and schedules remain frozen.
[Selection, attribution/budget audit, verified downloads and live-owner receipt](results/commons-local-stage-download-v1.json).

The selection reads the original `/mnt/external/qi` index read-only. All1188
SHA-1 identities are unique and absent from its172,372 downloaded entries.
Sources pass the existing project license policy, photographic eligibility,
minimum2048px sides, maximum120MP and256MiB/file bounds. Deterministic page-ID
hash ordering samples across the remaining queue. This does not establish
semantic scene diversity or source-family independence.

Full original attribution records, credit/artist HTML, license URLs and source
metadata are preserved in the local SQLite index and frozen selection JSON.
The existing `pupphoto` downloader and its config module are copied byte-for-byte
into the stage; credentials/config contents are not copied. Original publication
still requires exact byte count and Commons SHA-1, with resumable partial files
and in-flight reserve accounting. The shared archive-download lock prevents
the usual resume command from starting a competing job.

The independent startup audit verifies every selected record against the source
index, budget and license policy, then rehashes12 actually completed files.
Eight guard tests cover invalid limits, insufficient space, changed root, and
tampered license/hash/attribution before download setup. Active training source
and input hashes remain exact while these local-only downloads progress.

These are quarantined originals. Later independent cache integrity, duplicate/
protected-scene and content screening, reserved split handling and a separate
frozen data recipe are required before training admission. Standing GFX and
siblings remain excluded. Retain the local selection/index when reconciling the
main archive later so these originals are not downloaded twice.

A separate [4×/8× preparation worker](commons-local-preparation.md) is now queued
behind the exact downloader's exit. Production preparation is pending; the
completed two-source fixture is engineering validation, not corpus admission.

Inspect the local `download.log`, `launch.json` and SQLite status without
starting another download. A stopped local job resumes with:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' PYTHONPATH="$PWD/src" .venv/bin/python3 -P \
  scripts/stage_commons_local.py run .cache/commons-qi-local-20261018-v1
```

For a future bounded batch, `select` requires a fresh local cache directory and
enough space for its entire payload plus the declared reserve. It refuses an
existing stage, competing archive lock or changed frozen source/selection.
The source archive index and original files are preserved.
