# Expanding the Commons archive

The bounded download **completed4,000 new originals /27.66GiB** on2026-10-22.
The archive now holds **182,117 downloaded originals**, up from178,117, and
remains partial. Every new file passed size and publisher-SHA1 verification;
the original controller and downloader exited. Three failed requests remain
recorded: two404s and one publisher-size mismatch, without automatic retry.

**A separate CPU job is preparing3,809 eligible arrivals at4× and8×**, launched
at21:26PDT. It excludes103 unsupported license labels and88 geometry failures,
and checks against all178,117 prior downloaded/prepared source identities.
The new data remains quarantined/reserved until complete cache/source/neighbor
review and a separate frozen recipe. Active V102/V103 inputs stay fixed.
[Completed download reconciliation and actual preparation launch](results/commons-post4000-preparation-launch-v1.json).

## Download result and current preparation

The completed download ran from14:32 to18:59PDT using two workers,
at most .25 request starts/second, a
**336 GiB free-space reserve**, a 4,000-completion limit and a 12-hour deadline.
It used nice10/idle I/O and the existing index without discovery or enrichment.
The unchanged downloader verified size/SHA1 before atomic publication; its
controller repeated those checks on all4,000 completed originals. Independent
count/metadata reconciliation confirms the full178,117→182,117 delta and checks
the whole-second timestamp boundary, with no omitted launch-second files.
[Original launch and capacity estimate](results/commons-bounded-download-launch-20261022-v1.json).

The3,809-source two-scale estimate is **23.876GiB**. At launch,336.83GiB free
covers that complete payload plus4GiB margin above a **288GiB reserve**.
The reserve leaves32GiB above the ongoing quality study's256GiB floor for its
remaining checkpoint/evaluation/full-frame writes. The job requires48GiB
available RAM stable for60s, uses one CPU worker/single-thread libraries,
nice10/idle I/O, hidden CUDA and a21,600s supervised bound. Guards stop work
without retry or partial admission.

The producer first rechecks selected original bytes and immutable attribution
against a short read-only index transaction, then prepares both cache scales,
audits all cache bytes/headers and the complete4×→area2 one-code bound, and
screens42 cached protected references plus GFX capture/series metadata. Existing
ingestion/color/safety operators match the previously executed fixture exactly.
No source HDD or personal RAW is needed. This is a live launch, not completed
caches or source-quality approval.
The first12 atomically published4× arrays independently pass whole-file SHA256,
uint16/HWC headers, geometry, deterministic splits and all original attribution
fields; all frozen source files remain exact. The producer and trainer were
confirmed live. [Actual startup sample](results/commons-post4000-preparation-startup-v1.json).
These checks use complete temporary-manifest rows and do not finalize a corpus.

A separate [source-contact queue](results/commons-post4000-contact-queue-v1.json)
waits for the **complete4× manifest, finalized error file and summary with zero
failures**, then renders all3,809 sources on39 sheets. It may run during8×
preparation, but refuses a partial manifest or incomplete source coverage.
Its explicit288GiB reserve retains48GiB RAM and all cache/source integrity
checks. Eight focused tests and an actual two-source queue/renderer fixture
pass; that fixture's PNG exactly matches the prechange renderer. Those two old
engineering thumbnails were viewed, not the new source population. Rendering
alone never supplies manual source-quality review or data admission.
Root:`/mnt/external/demosaic/commons-post4000-contact-queue-20261022-v1/`.

Current root: `/mnt/external/demosaic/commons-post4000-preparation-20261022-v1/`.
`launch.json` records the exact timeout supervisor; `status.json` records the
worker's PID/creation time and stage. Results will appear under`work/outputs/`.

```bash
cat /mnt/external/demosaic/commons-post4000-preparation-20261022-v1/status.json
tail -10 /mnt/external/demosaic/commons-post4000-preparation-20261022-v1/worker.log
```

Completed download evidence remains under
`.cache/current-quality-20261022-v1/commons-bounded-download-v1/`:

- `plan.json` / `launch.json`: frozen limits, source hashes and owned processes;
- `status.json` / `controller.log`: terminal result and reserve/deadline checks;
- `download.log` / `worker.log`: actual downloader progress;
- `new-originals.jsonl`: all4,000 completed original records after size/SHA1 audit.

Inspect the completed download:

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

The completed download retained its336GiB reserve. Its lock is now available to
the cache producer; another cooperating download cannot run while preparation
holds it. Storage sharing did not change source admission or numerical recipes.

The preparation/review-freeze tools now accept an explicitly budgeted reserve
of at least256GiB, while retaining their historical560/500GiB defaults. Before
preparation, free space must cover **the entire new4×/8× payload plus4GiB margin
above the selected reserve**; the48GiB available-memory guard also remains.
For this bounded batch,288GiB is the frozen reserve:256GiB for the active
quality study plus32GiB for its remaining checkpoint/evaluation/full-frame
writes. The actual audited selection/payload and available storage were
recalculated before launch. This changes no existing quality-study plan.
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
`QI_ROOT` and `QI_LOG_FILE`; its defaults differ from the completed bounded
plan above. Do not start it alongside the cache producer. `scripts/expand_commons.py`
and `scripts/rebin_commons_extension.py` implement earlier selection/preparation
workflows. New arrivals use `scripts/prepare_downloaded_commons.py` for a frozen
selection, verified original/attribution bytes, both cache scales and protected
screening. It acquires the same download lock, after the original downloader
exits. All prior prepared/quarantined/failed identities must
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
