# Preserve evaluation headroom by sharing identical immutable checkpoint copies

Recorded: 2026-10-24T02:29:54-07:00 (America/Los_Angeles).

The matched V111/V112 GPU workflow is live. Before its remaining color arrays,
full-frame exports and subsequent eight-view evaluation, free space was about
276.36GiB. The estimated remaining 10.29GiB of outputs before eight-view quality
would have left less than its existing 270GiB startup requirement.

I consolidated thirteen duplicate immutable checkpoint-copy groups in nine
explicitly named project-owned evaluation roots. Each copy and existing global
cache entry was SHA256-verified, read-only and on the same filesystem. For each
group, all inode aliases were accounted for before replacing its cache and
report paths atomically with hard links to the identical global entry under
cache locks. All 36 existing paths retain identical bytes, sizes and mode0444;
their inode and modification time may differ. No training/canonical source or
receipt was replaced. This reclaimed **6.37573GiB**, leaving **282.73784GiB**
free at verification.

The first preparation stopped before publishing a plan or replacing anything:
one V101 copy had seven links but only six aliases inside its artifact root.
That source and its failure record are preserved. The next source excluded
the entire V101 root and completed its frozen plan without retries.

[Verification receipt](../docs/results/immutable-checkpoint-copy-headroom-v1.json),
SHA256 `a28a2a3df59fbba2be09bcc2d1413232cdcf3636ecbc7ab9226c3f3c92ff6bb6`.
It binds the actual plan, executed source, result, initial failure, thirteen
copy groups and original workflow references. Twelve protected original plans
and seven queued workflow references remain byte-identical. All six original
GPU controller/worker handles were verified live with matching creation times.
No process was restarted and no neural inference was added.

Estimated eight-view startup free space is now 272.45GiB after the remaining
color arrays (3.45GiB), original full GFX exports (5.70GiB) and eight-view full
GFX exports (1.14GiB). The unchanged live checks remain authoritative:
270GiB before startup and 256GiB during execution. This is storage headroom,
not a quality or speed measurement.
