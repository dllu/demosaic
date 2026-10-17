# Next Commons arrivals: separate fifth snapshot

A CPU-only job is preparing **10,368 newly downloaded eligible images** in a
separate staging corpus. It uses the same linear-light 8× binning, protected-scene
screen and duplicate audit as the completed fourth snapshot. Current training,
validation and test inputs remain fixed. No model uses these new candidates.

[Actual launch and independent startup checks](results/commons-incoming-v5-launch.json).
[Queued complete cache/membership audit](results/commons-incoming-v5-independent8-queue.json).
[Completed 75,806-source future corpus used as the base](commons-incoming-v4.md).

The frozen selection contains committed completed downloads absent from all
**84,959 prior candidate/failure identities**, including earlier quarantines and
decode failures. Its download timestamps range from 2026-10-17 01:56:17 to
08:17:00 UTC. There is no date cutoff; later arrivals cannot change the selected
membership. The read-only SQLite connection closes after materializing metadata,
before image decoding starts. The existing downloader continues independently;
no duplicate downloader was started.

Selection requires accepted CC BY, CC BY-SA, CC0 or public-domain metadata,
at least 2048 pixels per side and at most 120 MP. Full source URLs, author,
license, credit and attribution remain in the frozen manifest. Originals on
the external SSD are read-only; no personal RAW or cold hard-drive path is opened.

Preparation uses two CPU workers at nice 5 with CUDA hidden. Estimated 8× cache
payload is **12.663 GB / 11.793 GiB**. Preparing every candidate at 4× would add
about 47.182 GiB; actual 4× preparation will select only the reviewed new training
members. Both estimates fit within the existing 512 GiB free-space reserve at
launch, with about 900 GiB free. The producer checks headroom before decoding and
before screening/auditing; this does not reserve space against unrelated writers.
Matching 4× preparation is still pending and is required before this data can
support augmentation before the final reduction.

The actual package, operators, standing GFX config and driver are copied into
the output before work begins. Preparation imports that archive. Independent
startup checks verify every selection identity, its accepted license/dimensions,
all exclusions and source hashes. Twelve actual published caches pass complete
SHA256, uint16/HWC, minimum-size, binning-recipe and exact attribution checks.
The actual producer is live at nice 5, CUDA hidden, with its preparation lock held.
The startup receipt records 100 prepared images and no failure. This is a startup
sample; complete verification and content review remain pending.

After preparation, the controller checks the 42 cached protected identity
references, including the standing DSCF3879/DSCF3880 scene and sibling metadata.
It runs the existing seven-view/eight-orientation screen and keeps every flag
quarantined. The subsequent near-duplicate audit uses the reviewed fourth
snapshot's 8× base. All old rows and held-out assignments remain anchored; new
holdout buckets are reserved outside active evaluation. Finite fingerprint and
metadata screening cannot establish arbitrary semantic scene disjointness.

The producer stops at `audited-quarantine8-awaiting-reviewed-freeze`. A second
owned CPU job waits for that exact successful producer exit, then independently
checks **every** new cache, attribution record, selection/failure identity and
old split assignment. It also creates 48 deterministic content thumbnails for
actual viewing. The new owner is live and child-free at launch with no audit
output. Both its actual live-owner gate and the underlying auditor reject
incomplete preparation before output. The future completed path remains pending.

Actual thumbnail review, a separately reviewed 8× freeze, matching 4× preparation
and complete 4× pixel checks remain required. No training admission, performance
gain or model promotion follows from this preparation. The running V67 original
10,000-update schedule retains its original 40,170-source Commons manifest.

Operational files:

- Producer PID 3023649 / creation 1792225018.76.
- Output `/mnt/external/demosaic/commons-incoming-20261017-v5-quarantine/`.
- Producer state `workflow.json`, identity `controller.json`, frozen
  `selection.jsonl`, `selection-recipe.json` and `source/` under that output.
- Producer log `.cache/prepare-commons-incoming-v5.log`.
- Independent-audit waiter PID 3025414 / creation 1792225177.38;
  `independent8-workflow.json`, `independent8-plan.json` and `independent8-source/`.
- Future audit output
  `/mnt/external/demosaic/benchmarks/commons-v5-8x-complete-integrity-v1/`.

Verify actual PID, creation time and process state before acting. Existing
controllers own these paths; do not start duplicate preparation or audits.
