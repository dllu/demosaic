# Fifth Commons snapshot: 85,048 future training sources

The reviewed fifth snapshot adds **9,242 training sources**, increasing the
separate future corpus from 75,806 to **85,048**. Matching 4× preparation is
running for those new training members only. The active V67 run retains its
original 40,170-source Commons manifest; no model uses this new snapshot.

[Reviewed 8× freeze](results/commons-incoming-v5-reviewed8.json),
[actual 4× launch and startup checks](results/commons-incoming-v5-rebin4-launch.json),
[original preparation launch](results/commons-incoming-v5-launch.json), and
[full cache-audit launch](results/commons-incoming-v5-independent8-queue.json).

| Bucket | Previous | Fifth snapshot | Added |
| --- | ---: | ---: | ---: |
| Train | 75,806 | 85,048 | 9,242 |
| Validation | 2,303 | 2,303 | 0 |
| Test | 2,255 | 2,255 | 0 |
| Reserved | 4,005 | 4,998 | 993 |
| Excluded | 27 | 32 | 5 |

Preparation completed **10,367 caches from 10,368 selected sources**, with one
ICC-transform failure. The protected-scene screen cleared 10,240 and quarantined
127; every flag stays out. The duplicate audit additionally excludes five new
members and reserves 993 new holdout members. All old rows and held-out
assignments remain exact. The original 2,303 validation and 2,255 test sources
are unchanged. Reserved arrivals do not enter active evaluation.

The separate complete audit checks every prepared cache SHA/header/uint16 HWC
shape/minimum dimensions, source/license metadata, selected/prepared/failed
identity partition, protected flags and base membership. All checks pass.
All **48 deterministic content thumbnails on three sheets** were actually
viewed: architecture, foliage, water/coasts, mountains/clouds, wildlife/macros,
vehicles, interiors, performance lighting, portraits and monochrome subjects.
No obvious corrupt render or implausible color appeared in this sample. This
spot check does not establish native sharpness/noise quality or inspect every
image. Finite metadata and perceptual fingerprints cannot prove arbitrary
semantic scene disjointness. No model performance gain is claimed.

The failed source is a valid grayscale JPEG with a gray ICC profile; its
[future-ingestion correction](gray-ICC-ingestion.md) has separate tests and
isolated diagnostic caches. Those repaired caches are not admitted here. This
snapshot and matching 4× work retain the actual archived original operator and
its one-error exclusion, preserving their frozen recipe.

Frozen 8× membership:
`/mnt/external/demosaic/commons-incoming-20261017-v5-quarantine/reviewed8/manifest.jsonl`.
SHA256: `c4db19459384a8f8c118017cac43c592cc0a17a6d74ac1bdd9bdb6613346fdbe`.

The selection contains committed completed downloads absent from all 84,959
prior candidate/failure identities, including earlier quarantines. Download
timestamps span 2026-10-17 01:56:17–08:17:00 UTC, with no date cutoff; later
arrivals do not change membership. Read-only SQLite metadata closes before
decoding. Sources require accepted CC BY/CC BY-SA/CC0/public-domain metadata,
at least 2048 pixels per side and at most 120 MP. URLs, author, license, credit
and attribution remain in the manifests. Only Commons files on the SSD were
read; no personal or cold-drive RAW was decoded. The downloader continues
independently. The 42 cached protected references and standing GFX scene/sibling
metadata remain anchored; the screen uses seven views and eight orientations.

The 4× producer selects exactly 9,242 new reviewed training sources, with
estimated 45.001 GB of new caches. It reuses the completed fourth snapshot's
4× base, including all 4,558 old held-out rows, instead of redecoding old sources.
Reserved/excluded/quarantined/failed sources are omitted. Two workers at nice 5,
CUDA hidden, retain a 512 GiB reserve plus estimated payload and 10 GiB startup
margin. About 872.93 GiB was free at startup. All selection identities/metadata
and the first 12 published cache SHAs/dtypes/shapes/minimum 512px dimensions pass
independent startup checks; 282 rows were observed then.

After the exact producer exits successfully, a waiting CPU auditor checks every
new 4× cache and its matching 8× cache, all old rows/heldouts and source metadata,
and rounded area2 against 8× across every new channel sample, with a maximum
one-uint16-code tolerance. It creates another 48 resized content thumbnails for
actual viewing. That complete path and final 4× content review are pending; no
partial 4× output is a training input.

Operational files under
`/mnt/external/demosaic/commons-incoming-20261017-v5-quarantine/`:

- Original producer 3023649 and complete 8× auditor 3025414 exited successfully.
- Frozen selection/recipe/source, protected screen, audit and `reviewed8/`.
- Complete8 integrity/content receipt:
  `/mnt/external/demosaic/benchmarks/commons-v5-8x-complete-integrity-v1/`.
- Live 4× producer PID 3113673 / creation 1792230336.69;
  `rebin4-controller.json`, `rebin4-plan.json`, `rebin4-workflow.json`,
  `rebin4-source/`, `extension4/`; log `.cache/rebin-commons-incoming-v5.log`.
- Independent 4× waiter PID 3114258 / creation 1792230466.84;
  `independent4-source/` and `independent4-workflow.json`; future output
  `/mnt/external/demosaic/benchmarks/commons-v5-4x-complete-integrity-v1/`.

Verify actual PID/creation/state before acting. The first launcher observation
expired during metadata loading; rechecking the same producer confirmed it live
and preparing caches. No restart or duplicate job was launched. Full 4× checks
and actual content review remain required before a future training recipe uses
this corpus. Current training, evaluation, checkpoints and reports remain fixed.
