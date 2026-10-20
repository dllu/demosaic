# Recovered partial-array duplicates and continued original20k run

Previous turn made progress by archiving two closed objective-engineering trees
without changing their file contents. This turn revalidated the same expanded
trainer3666689/1792421187.78 and controller3343889/1792403189.77, then monitored
from12350 toward the original20k endpoint. The run passed14350 and later15600
with finite logged losses/gradient norms. Temporary RAM dips reached24.0/26.8GiB
during build activity; immediate samples recovered above50GiB and confirmed the
same live owner. The frozen24GB guard never stopped this run. No process was
signaled, no training state or plan was changed, and no quality inference ran.

Root space then fell to142GiB. Comparable completed reviews occupy about4–6GiB;
the current frozen review was kept unchanged. A read-only inventory identified
771 partial4x NPY files left by the earlier failed Commons preparer. Its successful
external-SSD recovery already contains matching regular files on another device.
No current plan directly references these arrays, no reachable active JSON names
the partial image directory, and neither frozen future890-source manifest points
its cache entries there. Parent metadata references remain intact.

After confirming both producer owners have exited and no active consumers hold
the partial image paths, fully hashed both copies of all771 arrays. Every pair
is identical. Captured source/canonical inode, device, byte count and mtime
properties. Published per-file aliases atomically with a temporary rollback
hardlink; verified each alias and canonical checksum before retiring the owned
NVMe copy. Exact partial filename membership remains771, with no extra completed
cache files exposed. Canonical recovered NPY contents/stat properties are unchanged.

An independent NumPy read validates every alias: all771 original partial manifest
rows equal the corresponding recovered rows, each file's SHA256 matches both
manifests, and each loaded NPY shape/uint16 dtype matches its record. All67
preserved metadata/source/recipe/error/status/plan/future-manifest refs rehash
exactly. The earlier failed preparation remains failed, with the same records
and source bytes; its cached array values are still available under the old names.
Resolved physical cache identities now belong to the successful SSD producer.
Use the completed recovered caches and fresh roots for future preparation.

Retired6,656,856,064 allocated bytes; payload6,655,281,954bytes(about6.2GiB).
Root free space increased from152,424,837,120 to159,078,539,264bytes (about148GiB
afterward); external free space remains601.9GiB. System activity can separately
change free-space measurements. No source image, private RAW/GFX cache, source
HDD, prepared pixel value, model checkpoint, data admission or runtime changed.

Executed driver, full inventory and receipts:
.cache/benchmarks/commons-partial-array-alias-20261019-v1/.
Public summary: docs/results/commons-partial-array-alias-20261019-v1.json.
The original20k endpoints and complete quality/native review remain required;
V43 stays the working reference. SOTA, broad real superiority and100MP/10s are
still unmet/unproven. The full goal remains active.
