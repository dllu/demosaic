# Preparing the newly downloaded Commons originals

A separate CPU job is preparing **4,337 new originals at both 4× and 8×**.
They come from the completed 4,557-file archive download and have not entered
training. Existing V86/V87 source membership, validation/test sets and the
standing GFX exclusions remain fixed. This is data preparation, without a
trained quality or scene-diversity claim.
[Actual launch and source bindings](results/commons-post4557-preparation-launch-v1.json).

Selection compares source SHA1 identities against the complete prior reviewed
8× corpus and all 1,188 earlier arrivals. It applies the existing free-license
whitelist, minimum 2,048px per side and maximum 120MP. The 220 omissions are
115 license labels outside that whitelist and 105 geometry failures. They stay
in the read-only archive. Selection uses no model output or image-content score.
Full source attribution is pinned in the original download snapshot.

The estimated two-scale payload is **27.524 GiB**, reusing the existing originals
directly rather than duplicating 29.470 GiB of source bytes. One CPU worker runs
at nice10 with single-threaded numerical libraries and hidden CUDA. Launch
requires room for the entire cache estimate plus4GiB margin above a **560GiB
external reserve** and **48GiB available RAM for60s**. Per-source memory/disk
guards stop this job before further decoding. A separate21600s timeout bounds
its own process group. Failure preserves partial output and does not restart or
change the trainer.

The worker verifies every selected live-index immutable metadata field, original
size and publisher SHA1, using a short read-only SQLite transaction. Existing
ICC/EXIF-aware linear-light ingestion writes atomic uint16 HWC arrays in a new
SSD root. Both scales retain deterministic source hash splits. Full cache bytes,
headers, attribution and prepared/error coverage are checked, followed by the
existing complete rounded4×→area2 versus direct8× one-code bound. The unchanged
protected-source screen uses42 cached references plus standing capture-name /
camera-date-family checks, without reading source HDDs or scoring model quality.

Screen-clear train hashes become `quarantine`; new validation/test hashes become
`reserved`. Protected flags stay withheld. Independent duplicate/content/known
series review and a coupled4×/8× admission freeze remain required. Finite
fingerprints do not prove scene independence. No partial output is a new corpus.

Ten focused tests pass, covering known/duplicate identities, unsupported licenses,
geometry, unfinished or corrupt downloads, changed attribution and resource
guards. The [actual two-source fixture](results/commons-post4557-CPU-check2-v1.json)
also verifies all original bytes/credits, all four arrays, both cache scales,
complete area checks and protected screening. Both resulting train hashes stay
quarantined. Every one of the full producer's50 frozen source files matches
that executed fixture; its45 package modules match the actual context trainer.
The production plan binds50 inputs. These are engineering checks, not evidence
that all4,337 sources are yet prepared or safe for training.

Operational root:
`/mnt/external/demosaic/commons-post4557-preparation-20261019-v1/`.
Its `status.json` records the exact owner, plan and current stage. The dated
launch observed PID257168/creation1792448532.19; check PID and creation time
together before acting. New arrays and receipts live under `work/outputs/`.
The archive/index and all original photos remain read-only.
