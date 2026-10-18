# Share future evaluation checkpoint copies

Kept the exact live mixed16 quarter owner2645898/1792305192.32 and training
child2645905/1792305192.6 running. The no-DINO arm advanced from6650/106400
to7150/114400 updates/examples during this work, approximately1.09s/update.
Quality owner2667688 and profile owner2714232 remain alive and child-free,
waiting in their original order. No recipe, frozen source or plan changed.

Found that the root evaluation snapshot helper copied a complete checkpoint
for every panel and used a shared fixed temporary name. Added a small shared
immutable checkpoint cache with the existing public helper re-exported from
suite. One opened source version is hashed/copied; unique temporaries and
per-digest flock handle concurrent evaluation. Verified read-only copies are
shared across panel paths on the same filesystem, with a separate verified
cross-filesystem fallback. Mutable source inodes stay separate. Existing valid
snapshots are preserved; corrupt/unsafe files are rejected without overwrite.
The running frozen workers retain the old implementation and are unaffected.

Twelve focused tests pass, including atomic source replacement, mutation during
copy, concurrent same/different panel requests, corruption, unsafe aliases,
read-only source reuse and EXDEV fallback. Combined with existing suite,
reporting and real-suite tests:22passed/3.71s. Ruff and diff whitespace pass.

Actual V43 checkpoint SHA
`0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5`
was tested by two overlapping CPU processes, four requests/two destinations.
One independent copy, three read-only links, complete hashes equal, original
source stats/bytes unchanged. Avoided531841024 allocated bytes relative to
two independent panel copies. No Torch import or network inference. Existing
canonical cache is retained for future panels. Free SSD about519.4GiB;
downloader stays stopped. This is no evaluation-speed measurement.

All372 unique files guarded by the three current frozen workflows pass before
and after; their plan hashes are unchanged. Private driver/result:
`/mnt/external/demosaic/benchmarks/checkpoint-cache-CPU-v1/`.
Result SHA
`10b4fa27bb41126b7cd10e8d0f4a90f1776eba60b3c8b2cf345513ef326f2dab`;
published exact copy in docs/results/checkpoint-cache-CPU-v1.json.
No new model report, quality promotion, timing claim, extra GPU job or training
membership change. Full10k matched review still pending; SOTA, decisive real
superiority and100MP/10s remain unmet/unproven.
