# Local-original reconciliation and bounded archive resume

All **1,188 originals / 17,175,771,412 bytes** have completed local preparation
and archive reconciliation under the
[memory-recovery plan](commons-local-memory-recovery.md). The bounded archive
download is running with two workers, .25 starts/second, a 608 GiB reserve and
10,000-file completion limit. As of 2026-10-19 11:13 UTC it had added
1,447 files / 9.8 GiB. Current state, exact owner/child identities, reconciliation
receipt and logs are under
`.cache/commons-archive-handoff-memory-recovery-20261019-v1/`.

The first worker stopped after local preparation failed its available-memory
guard; it did not reconcile or download. That failed observation and the
[original queue/fixture receipt](results/commons-archive-handoff-queue-v1.json)
remain preserved. Recovery used a fresh root after successful preparation.

At reconciliation, the selected archive rows matched the local-selection snapshot.
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

This is archive bookkeeping and downloading. New sources remain out
of the running V84/V85 corpora; duplicate/content review and a separately frozen
data recipe remain required. Standing GFX and siblings stay excluded. No model
quality, scene independence or training benefit is established here.
