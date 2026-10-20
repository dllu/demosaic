# Verified original-cache aliases and continued training

The previous turn made progress by checking retained4k states and recovering
9.25GiB from unused generated test fixtures. This turn revalidated the same
expanded trainer3666689/1792421187.78 and controller3343889/1792403189.77.
Training advanced from4600 through7575 while the original20k study stayed fixed.
Three early memory warnings observed RAM around39.9,32.2 and26.7GiB during
compiler/linker activity; immediate follow-ups recovered to54–62GiB with the
same live trainer and finite logged values. The actual frozen trainer checks
its24GB available-memory guard every50 steps and saves before raising if it
fires. It never stopped or restarted. Read-only observers ended for inspection;
none signaled or changed the trainer or another process.

Inspected the native and Commons loaders: both already memory-map uncompressed
caches and convert the selected crop. No full-image decode change is needed.
No runtime source, data recipe, inference or loss change was made.

Root space then fell to138GiB during continuing build activity, despite the
prior test-cache cleanup. The current study's total directory occupies5.2GiB.
The completed local Commons stage held1188 originals whose exact copies had
already been reconciled into the canonical external SSD archive. All four
active plans have no literal or resolved references to those local image paths;
all exact local download/preparation/archive owners have exited. Same-user
command/cwd and project FD checks find no local-image consumers. An exclusive
shared archive-download lock protects the operation.

Every local and canonical file was fully reread for SHA1 and SHA256. All1188
pairs match, covering17,175,771,412 payload bytes. Canonical byte counts and
inode/mtime properties remain unchanged; all1188 source/attribution archive
rows match their reconciliation snapshot. The local source index, selection,
four active plans and both future890-source manifests retain exact hashes.

The initial directory-wide alias would expose extra archive filenames. The
final layout instead has a regular local images directory with exactly1188
individual file aliases, preserving the original filename roster. All aliases
resolve to the verified canonical SSD files. The original ownership/inode/hash
inventory and both executed drivers/receipts are preserved. Only the owned
NVMe duplicate copies were unlinked, freeing17,178,230,784 allocated bytes
(about16GiB). No new external copies or image transformations were made.
Root free space returned to about154GiB; external free space stays608GiB.
Concurrent system activity affects free-space measurements independently.

The old local image names remain usable for read-only source access, with
resolved file identity now belonging to the archive. Do not rerun the completed
local downloader into this alias directory. Historical receipts preserve the
original cache identities; the new mapping is recorded explicitly. Current
training and prepared cache arrays are unaffected. The private GFX RAF cache
and personal source drives were not accessed or modified.

Public receipt: docs/results/commons-local-original-cache-alias-20261019-v1.json.
The full final20k quality/native review remains queued, and the deferred GPU
precision candidate still waits for those exact work owners. V43 remains the
working reference. SOTA, broad real superiority and100MP/10s remain unmet or
unproven; the full goal stays active.
