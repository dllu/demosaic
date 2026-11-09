# Storage maintenance

The follow-up 2026-11-08 cleanup consolidated **133.724 GiB** of byte-identical
archives: **133.589 GiB externally** and **0.135 GiB locally**. All 42,761
original artifact paths survive in 11,829 read-only shared groups. It also
removed seven inactive generated test/compiler directories (170,074,112 bytes)
and the package download cache. The package tool reported 5.3 GiB of logical
files, but most already shared storage with installed packages; that is not
5.3 GiB of additional disk savings. The installed environment still imports.

The cleanup offloaded **93.092 GiB** of old full-resolution NumPy/TIFF render
evidence to `/mnt/external/demosaic/cold-full-frame-20261108-v1/`. These are 126
unique files with 127 original paths, now individual file symlinks. Every file
was checked by full SHA256, and NumPy/TIFF readers were checked through the
original paths. No directory, checkpoint, frozen source, receipt, native crop,
original photo or protected GFX cache was relocated. Existing receipt bytes
remain unchanged. A strict historical check that compares `Path.resolve()`
strings must account for the recorded relocation map; ordinary original-path
reads retain the same bytes, dimensions, data types and sampled pixels.
After verification, free space was **230.424 GiB locally** and
**151.874 GiB externally** (up from 137.299 /
111.377 GiB). Local project allocation is
451.088 GiB.
[Follow-up receipt, relocation map and operation journals](results/storage-maintenance-20261108-v2.json).

The earlier same-day local cleanup reclaimed **114.534 GiB**: **110.233 GiB** of
byte-identical historical artifacts and **4.301 GiB** of inactive generated
test/compiler caches. Project allocation fell from approximately 658 to 542.745 GiB;
local disk availability was 146.821 GiB after verification. `/mnt/external`
remained unchanged at 111.377 GiB available; no offload was needed.
[Verified receipt, original metadata and operation journals](results/storage-maintenance-20261108-v1.json).

The duplicate consolidation retained 30,293 paths in 5,892 groups, replacing 23,438
redundant path allocations. Most savings came from repeated manifests
(53.875 GiB), NumPy arrays/archives (49.426 GiB), and model snapshots (6.194 GiB).
All groups were rehashed after replacement, all aliases were checked again at
completion, and current V187/V193 checkpoint hashes, V193/V195 sealed bindings,
and all 103 neural source hashes still matched. The two protected GFX caches
remain local. The cleanup removed 34 stale generated cache directories containing
37,764 files; recent compiler/test caches were left in place.

Keep unique experiment evidence, checkpoints, frozen source, machine receipts
and the two protected GFX photo caches. Historical artifacts can share storage
when their complete file bytes match. Removing old generated pytest fixtures
and compiler caches is also safe after confirming that no worker uses them.

`scripts/compact_historical_cache.py` plans and applies hard-link consolidation
inside explicitly selected repository `.cache` directories. It excludes symlinks,
files modified within two days, files under 64 KiB, and inodes with aliases
outside the selected inventory. It checks for active Python workers and open
candidate files. Sampled content only filters candidates; full SHA256 hashes
determine equality. Files with different modes or ownership remain separate.

`scripts/compact_project_archives.py` extends that unchanged engine to explicitly
selected project-owned `/mnt/external/demosaic` archives and additional image
and weight suffixes. It excludes the protected local GFX caches and original
photo locations. Its mandatory policy sidecar binds the adapter, original
engine, roots, suffixes and complete hashed plan. Use its `plan` and `apply`
commands with the same arguments shown below when consolidating external
archives; preserve the generated `.policy.json` beside the plan.

```bash
source scripts/env.sh
mkdir -p .cache/storage-review
uv run python scripts/compact_historical_cache.py plan \
  --root .cache/quality-20261102 \
  --root .cache/quality-20261103 \
  --output .cache/storage-review/plan.json.gz
# Inspect the plan and its expected_reclaimed_bytes before applying it.
uv run python scripts/compact_historical_cache.py apply \
  --plan .cache/storage-review/plan.json.gz \
  --journal .cache/storage-review/applied.jsonl \
  --output .cache/storage-review/result.json
```

Application checks identities against the plan, records durable intent, replaces
duplicate paths atomically, and rehashes every resulting group. All original
paths and file bytes survive. Shared files become read-only; aliases acquire
the anchor's modification time and inode, and link counts/ctime change. Original
metadata is retained in the plan. Copy a historical checkpoint or other artifact
to a new writable file before modifying it or resuming training. Do not edit
shared frozen source in place.

For future experiments, reuse immutable datasets, manifests and model snapshots
instead of copying them into every frozen work directory. Keep current training
outputs writable and separate. Budget disk space before recording full arrays;
retain native crops and sufficient scientific evidence without producing a
fresh copy of every historical comparison panel. Use `/mnt/external/demosaic`
for larger new outputs when it has adequate room, and keep the GFX RAF caches
local as required by `AGENTS.md`.

Moving an old directory behind a symlink can change resolved paths in sealed
plans. Prefer consolidation when it provides enough room; any future offload
needs an explicit relocation record and verification of the existing readers.
The full-frame offload above uses individual file links, leaves all directory
paths intact, and records every old/new file mapping. Current V200 publication
files and checkpoint/export hashes were verified unchanged; the selected old
full-frame paths were absent from the current review's plain JSON/Python
sources. Preserve those links when making backups, or follow them explicitly
when a backup must contain the full image payloads.
