# Shared immutable evaluation checkpoint snapshots

Future evaluation panels share a verified checkpoint copy through
`demosaic.checkpoint_cache.freeze_checkpoint`. Existing callers continue to import
the helper from `demosaic.suite`; report paths remain `weights/weights-SHA256.pt`.
For the usual `evaluation/PANEL/weights` destination, the shared cache is
`evaluation/.checkpoint-cache`. An explicit `cache_dir` is also supported.

The helper hashes one opened source inode, then copies that same version on a
cache miss. Atomic training saves cannot mix checkpoint versions. A per-digest
process lock and unique temporary files protect concurrent requests. Only a
complete, checksum-verified, read-only copy is published; panel paths hard-link
that copy on the same filesystem. Mutable training/archive inodes are never
linked into the cache. Cross-filesystem destinations receive a verified separate
copy. Corrupt existing files are rejected and preserved. Existing valid report
snapshots retain their bytes and inode.

This changes checkpoint storage, with no model computation or quality claim.
The active mixed16 quarter training, review and profiler use their preserved
sources and retain their previous snapshot implementation. No frozen workflow
was edited to adopt this helper.

## Verification

The [actual CPU proof](results/checkpoint-cache-CPU-v1.json) used V43 checkpoint
SHA256 `0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5`.
Two processes made four requests for two report destinations. Exactly one copy
was made; both report paths and the cache shared one read-only inode, distinct
from the unchanged source inode. Every resulting file matched the full source
hash. The two report destinations avoided 531,841,024 allocated bytes relative
to two independent copies, approximately 507 MiB. This is a storage measurement;
no end-to-end evaluation speedup was measured.

All 372 unique frozen input/source checks across the active training and queued
review/profile plans passed before and after. The proof did not import Torch.
Its preserved driver is
`/mnt/external/demosaic/benchmarks/checkpoint-cache-CPU-v1/probe.py`; result SHA256
is `10b4fa27bb41126b7cd10e8d0f4a90f1776eba60b3c8b2cf345513ef326f2dab`.

The 12 cache tests cover concurrent requests, atomic source replacement,
in-place source mutation, corrupt snapshots/cache, unsafe aliases, repeat reuse,
and cross-filesystem fallback. Together with existing suite/reporting/real-suite
tests, 22 tests pass. Ruff and whitespace checks pass.

The [completed-copy storage record](results/completed-evaluation-snapshot-storage-v1.json)
also covers older evaluations that retain their frozen implementations. Its
fourth operation shares 46 byte-identical copies across 11 checkpoints from six
completed reviews, recovering another 11.22 GiB. Original archives remain
separate. The [independent audit](results/completed-evaluation-snapshot-storage-v4-audit.json)
checks all 61 snapshot paths, 11 original archives, 886 report/metric/native-PNG
hashes and 372 current workflow input/source hashes. The preceding review used
16.40 GiB when every output path is counted independently. After consolidation,
530.62 GiB is free; allowing 24 GiB for review and 1 GiB for remaining checkpoint
growth leaves an estimated 5.62 GiB above the 500 GiB queue reserve. This estimate
cannot guarantee future space on the shared filesystem. The downloader remains stopped.
