# Expanding the Commons archive

A **bounded download of up to 4,000 more originals is running**, started on
2026-10-22 at **14:32 PDT**. It uses the existing Commons Quality Images index
at `/mnt/external/qi`, without discovery or attribution enrichment. The archive
is still partial: before this run it held **178,117 originals / 754.7 GiB**, with
**279,548 pending**. Completion of an earlier bounded batch did not complete the
archive. At 14:42 PDT, 162 additional originals had been published; this is a
progress observation, not a final byte audit.

[Launch, capacity estimate, live owners and isolation receipt](results/commons-bounded-download-launch-20261022-v1.json).

## Current limits and progress

The singleton job has two workers, at most .25 request starts/second, a
**336 GiB free-space reserve**, a 4,000-completion limit and a 12-hour deadline.
It runs at nice10 with idle I/O priority. The unchanged downloader resumes
partials and verifies publisher size/SHA1 before atomic publication. The shared
lock is inherited by the child, so another cooperating launcher cannot start
while that downloader remains alive.

Metadata for the next 4,000 queued originals estimates **27.66 GiB of original
files**. About **3,912** meet the current 2,048-pixel minimum short side; their
4×/8× uint16 caches would add about **24.47 GiB**, before audit overhead and
exclusions. These are estimates, not admissions. Free space was about374GiB at
the launch-receipt observation; the bounded budget leaves room for the active
quality study and its planned full-frame exports. The entire pending archive
would exceed available capacity.

Operational files are under
`.cache/current-quality-20261022-v1/commons-bounded-download-v1/`:

- `plan.json` / `launch.json`: frozen limits, source hashes and owned processes;
- `status.json` / `controller.log`: current phase and reserve/deadline checks;
- `download.log` / `worker.log`: actual downloader progress;
- `new-originals.jsonl`: produced at termination after independent size/SHA1 audit.

Inspect the existing job without starting another:

```bash
tail -10 .cache/current-quality-20261022-v1/commons-bounded-download-v1/download.log
cat .cache/current-quality-20261022-v1/commons-bounded-download-v1/status.json
```

The cooperative lock is `.cache/commons-qi-download.lock`. Check the recorded
PID **and process creation time** before signaling an owned process. The
controller terminates only its matching child on its deadline or guard failure;
it does not automatically retry a failed job. Originals and attribution remain
in the archive after a normal reserve/limit stop.

## SSD capacity for the download

Verified duplicate frozen evaluation weights now share read-only filesystem
storage. This released **6.96 GiB** of allocated blocks by relinking 137 duplicate
copies into 31 shared objects, preserving all 168 artifact paths and checkpoint
bytes/hashes. Whole-file SHA256 checks passed before and after replacement;
the shared objects passed the actual immutable checkpoint-cache validation.
Prior per-path modes/mtimes remain in the restoration ledger. Working training
checkpoints, canonical models, originals and prepared data were not relinked.
[Completed storage and active-plan verification](results/frozen-evaluation-weight-sharing-v1.json).

The original bounded downloader remains the only owner of the archive download
lock. This storage change increases its headroom without changing the 336 GiB
reserve, current manifests, source admission policy or numerical experiments.

The preparation/review-freeze tools now accept an explicitly budgeted reserve
of at least256GiB, while retaining their historical560/500GiB defaults. Before
preparation, free space must cover **the entire new4×/8× payload plus4GiB margin
above the selected reserve**; the48GiB available-memory guard also remains.
For this bounded batch,288GiB is a prospective reserve:256GiB for the active
quality study plus32GiB for its remaining checkpoint/evaluation/full-frame
writes. The actual audited arrivals, free space and remaining writes must be
recalculated before launch. This changes no running plan or downloader limit.
[Resource-policy changes and37 passing focused tests](results/commons-bounded-preparation-budget-v1.json).

## Admission into a future training corpus

**Downloading does not change a training or evaluation manifest.** V100/V101
retain their frozen 88,484-source cohort and original numerical snapshots.
V102/V103 use their separately frozen 88,477-source cohort; new downloads do
not change any of these recipes.
Their training, evaluation and full-frame plans do not bind the live archive
SQLite index. New arrivals require separate two-scale preparation,
protected-scene and duplicate screening, source-quality review and a frozen
manifest before any later training experiment.

The [completed 4,557-original batch](commons-post4557-preparation.md) prepared
4,337 suitable arrivals at both scales. Its [reviewed extension](commons-post4557-reviewed.md)
added 2,751 training sources to produce the 88,508-source pool. Subsequent
[high-loss/source-quality review](corpus-source-review.md) produced the completed V100/V101
88,484-source cohort and the current V102/V103 88,477-source cohort. See
[quality-first training](quality-first-training.md) for the current recipes.
Validation/test membership and the protected GFX scene/siblings remain fixed.

Preparation uses geometry on the 4× cache followed by the final 2× area
reduction. The [training pipeline](training-pipeline.md) describes this order
and the current augmentation choices. New sources should reuse existing checked
originals and caches instead of decoding old corpus members again. A completed
freeze must preserve old split/source records and publish checked new cache
headers/hashes; partial producers never enter training.

## Existing tools and completed evidence

`scripts/resume_commons_qi.sh` is the generic cooperating launcher. It supports
`QI_RESERVE_GIB`, `QI_WORKERS`, `QI_REQUESTS_PER_SECOND`, `QI_DOWNLOADER`,
`QI_ROOT` and `QI_LOG_FILE`; its defaults differ from the **current bounded
plan above**. Do not start it alongside that job. `scripts/expand_commons.py`
and `scripts/rebin_commons_extension.py` implement earlier selection/preparation
workflows. New arrivals use `scripts/prepare_downloaded_commons.py` for a frozen
selection, verified original/attribution bytes, both cache scales and protected
screening. It acquires the same download lock, so preparation starts after the
current downloader exits. All prior prepared/quarantined/failed identities must
be excluded. Follow the [completed preparation](commons-post4557-preparation.md)
and [reviewed coupled freeze](commons-post4557-reviewed.md) for the independent
cache/source/neighbor review required before admission.

Preserved completed receipts include:

- [October19 reconciliation and reserve stop](results/commons-bounded-reserve-stop-20261019-v1.json):
  4,557 new originals /31.0GiB; every new size/SHA1 checked, 1,188 reconciled
  rows retain immutable attribution, and both owned processes exited0.
- [Original extension and split/duplicate audit](results/commons-extension-20261016-v1.json).
- [Complete 4× base/extension freezes](results/commons-four-complete.json).
- [Matched native-cache precision checks](results/commons-augmentation-pilot-startup.json):
  unaugmented 4×→area2 differs from direct8× by at most one uint16 code.
- [Preparation worker measurements](results/commons4-preparation-workers-v1.json):
  all48 cache hashes matched across six timed cases. This measures preparation,
  not model-training speed.

The timestamped diary retains earlier download/preparation chronology. The
receipts preserve exact historical parameters and bytes.
