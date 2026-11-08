# Storage maintenance

The 2026-11-08 cleanup reclaimed **114.534 GiB**: **110.233 GiB** of
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
