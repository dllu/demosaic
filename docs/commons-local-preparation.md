# Queued local Commons cache preparation

An isolated CPU worker waits for the [bounded local download](commons-local-staging.md)
to finish, then prepares both **4× and8× linear uint16 caches**. The full selected
batch needs approximately9.40GiB and2.35GiB respectively, excluding small headers
and manifests. This supports the existing4× → geometry/PSF → area2 training
path while retaining a direct8× comparison. The running V82/V83 recipe remains
frozen. No newly staged source enters training.
[Live-owner, frozen-source/input checks and actual fixture receipt](results/commons-local-preparation-queue-v1.json).

The worker verifies the downloader's PID and creation time, waits for its exit,
then claims the shared archive-download lock. Any unfinished index rows stop
preparation. Every selected row must retain its immutable source/attribution
fields. Every completed original is independently checked against its expected
byte count and Commons SHA1; download failures remain separately recorded.
Originals and the main archive/index stay read-only.

Preparation uses the unchanged ingestion operator, one CPU worker, nice10,
single-threaded numerical libraries and hidden CUDA. It retains at least200GiB
local free space and24GiB available RAM, checking before each source. Launch
space includes all selected original bytes, the estimated two-scale cache
payload and4GiB margin. The downloader retains its own224GiB reserve. No model
profiling, inference, optimization or active-data change is performed.

The completed-cache audit rehashes every published cache, checks uint16 HWC
shape/minimum size, attribution and exact prepared/error identity partition,
then compares rounded area2 from4× against direct8× over every common source.
The maximum allowed difference is one uint16 code. Existing seven-view/eight-
orientation screening checks the42 cached protected scenes and standing GFX
capture identifiers/camera-date family without reading cold-drive originals.
Screened arrivals remain `quarantine`; new validation/test hash buckets remain
`reserved`. Neither list is a training manifest. Duplicate/content/known-series
review, manual content inspection, matching4×/8× membership and a separate data
recipe are still required. Finite fingerprints do not prove scene independence.

Eight tests pass, covering low disk/RAM budgets, unfinished download rows,
modified attribution, corrupt original bytes and a two-code saved-cache area
error even when file hashes match. A complete frozen-worker fixture using two
real locally cached Commons originals passes original verification, both cache
preparations and all42 protected-reference checks. Its1,328,802 area samples
agree within one code; one training hash stays quarantined and one validation
hash reserved. CUDA stays uninitialized. This is ingestion engineering evidence,
not model performance or a review of all1,188 selected sources.

The initial fixture had no completed pair under its5MB sample cap and stopped
before launching a worker. A subsequent fixture confirmed the worker imports
no Torch/CUDA while waiting, then correctly refused the live archive lock. Both
failures are retained. The successful isolated fixture uses its own test lock;
the production worker keeps the real shared lock and all input/source checks.

Operational files:

- Queue: `.cache/commons-qi-local-preparation-20261019-v1/`.
- Actual owner at launch: PID3057802, creation1792390034.78. Verify both identity
  and live state before acting; a status file alone is not liveness evidence.
- Frozen47-source worker,49 immutable inputs and plan: `work/`, `plan.json`.
- Progress: `status.json`, `controller.log`, `startup-observation.json`.
- Future caches/audit/screen: `work/outputs/`; production completion is pending.
- Successful fixture: `.cache/benchmarks/commons-local-preparation-preflight-v3/`.

The worker stops on failed guards and preserves its output for inspection.
Do not start a duplicate while its exact owner is live or treat partial caches
as a reviewed corpus. No model-quality gain is claimed.
