# Local-original reconciliation and archive resume: deferred

The local batch has downloaded all**1,188 originals /17,175,771,412bytes**.
A separate worker waited for the exact local downloader and cache preparer to
exit. It then stopped because preparation had failed its available-memory guard.
**Archive reconciliation and broader downloading did not begin.** Recovery is
deferred until the [GPU recovery and review](bank-detachment-memory-recovery.md)
finish, followed by successful cache preparation under a fresh plan. The
implementation and completed fixture below remain valid engineering evidence.
[Verified live queue, source bindings and full fixture](results/commons-archive-handoff-queue-v1.json).

The original archive index still matches the snapshot used for local selection.
The handoff takes the shared download lock and verifies that every immutable
source/attribution field agrees among the frozen selection, local index and
archive index. Complete source SHA1/byte checks guard new atomic copies to the
canonical archive paths. Existing archive images are verified and reused;
conflicts stop the operation. Local originals/index remain unchanged.

After copying succeeds, one guarded transaction marks only the completed local
sources downloaded in the main index. It changes operational download fields,
preserving attribution, other rows and archive state keys. Before/after selected
rows and exact status-count changes are recorded. Repeating reconciliation
reuses verified files and downloaded rows without incrementing attempts again.
Local failures stay pending in the main archive for ordinary future retries.

The same lock remains held across the subsequent unchanged download-only CLI:
two workers, at most.25 request starts/second, a**608GiB reserve** and at most
10,000 additional completed files. This stricter reserve leaves room for future
caches and model work. The controller records the exact child identity/exit;
the child inherits the archive lock. CPU nice10, idle I/O and hidden CUDA protect
ongoing training. No Torch/CUDA library or child is loaded while waiting.

Eight tests pass in2.87s: metadata corruption, incomplete sources, low space,
bad source/destination bytes, idempotency and failed-publication rollback.
A complete frozen-worker fixture copies and indexes two real cached Commons
originals in a separate archive. Their attribution remains exact. The actual
unchanged downloader finds no pending files and exits0 without image downloads.
The fixture uses its own lock; production retains the real shared lock.

Original queue: `.cache/commons-archive-handoff-20261019-v1/`, owner3126300 /
creation1792393569.12 at launch. That owner has exited with
`failed-archive-handoff-no-automatic-retry`; preserve its failed snapshot.
Its frozen plan/source, `status.json`, `controller.log` and future
`reconciliation/receipt.json`/`download.log` record actual progress. The complete
fixture is `.cache/benchmarks/commons-archive-handoff-preflight-v1/`.

This is archive bookkeeping and download preparation. New sources remain out
of the running V82/V83 corpora; duplicate/content review and a separately frozen
data recipe remain required. Standing GFX and siblings stay excluded. No model
quality, scene independence or training benefit is established here.
