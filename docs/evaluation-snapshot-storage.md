# Recovered storage for additional Commons data

Verified consolidation reclaimed **168.82GiB** from367 checkpoint copies across
66 model hashes. External free space increased from502.11GiB to670.93GiB.
Every snapshot path and byte is preserved; duplicates share read-only evaluation
storage. Images, scores, native crops, training and data membership are unchanged.
[Completed operation and independent audit](results/completed-evaluation-snapshot-consolidation-v1.json).

The read-only inventory sampled936 large files. Sample hashes identify possible
duplicates; they do not prove full-file equality. Only content-addressed
checkpoints bound to completed report model entries are eligible. TIFFs/arrays/
images are outside the operation. Every selected snapshot is fully SHA256-
checked before replacement. Active input directories/inodes and all discovered
original archive inodes are excluded. Archives stay physically separate.

The operator uses per-checkpoint locks, CPU nice15 and idle I/O priority. Each
atomic replacement retains the old inode until its post-check succeeds; a failed
check restores it. Seven tests cover corruption, writable canonical copies,
unexpected/archival aliases, escaped paths and rollback after replacement.
A complete three-copy fixture also passes, preserving its writable archive.

After the exact operator exits, an independent auditor rehashes all66 canonical
files and verifies all367 aliases share those exact read-only inodes. It checks
all637 active source/input hashes,5,593 report/metric/native artifact hashes and
410 original archive properties. All checks pass, with no leftover replacement
links. Available-space growth agrees with reclaimed allocations to8KiB of
filesystem metadata overhead. Both actual owners have exited.

At publication, detached V83 was live at step1,100/4,000; local Commons downloading
and its queued preparer remain active. Restored external headroom exceeds the
512GiB archive reserve. The local batch stays frozen; its downloaded identities
must be reconciled before a broader resume to avoid duplicate downloading.
No second download, data admission or model-quality result is part of this work.

Plan, source copy, original properties, change ledger, process identities,
operator result and independent auditor source/log/receipt are retained in
`.cache/benchmarks/completed-evaluation-snapshot-consolidation-20261018-v2/`.
The reusable operator is `scripts/consolidate_evaluation_snapshots.py`.
The [cumulative receipt](results/completed-evaluation-snapshot-storage-v1.json)
records201.42GiB recovered across five completed operations.
