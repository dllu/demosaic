# Expanded retained 4k state and local cache headroom

Previous goal turn was a verified wait with finite retained 1k states and exact
cross-arm RNG/logged shared inputs. This turn revalidated the exact expanded
trainer 3666689 / 1792421187.78 and monitored it from 1175 through 4025, without
changing training or launching inference. Available RAM stayed around 59–64 GiB.
The same original 20k controller remains live; quality and deferred precision
workers remain childless. No job was restarted or stopped.

CPU-only inspection of both closed retained 4k checkpoints verifies finite
91-model/91-EMA/89-AdamW states, nonnegative second moments and all counters at
4000. Optimizer groups and Python/CPU/CUDA RNG states match exactly at this
boundary. LR 9.206544616434249e-6 independently matches the original 20k cosine
with 10% floor. All 130 recorded shared-domain pairs match; all 46 native pairs
differ. The source archives differ only in raw-clean-manifest.json. Control
checkpoint SHA is 7d8f8f99560bce16a60c257ef16820dd40ed2b63b236ff381b5d9ef9989e37fa;
expanded SHA is 99e0288916f6c15f616fb6e029184c9ecd9e8e0a62d47e8ebd80af44039f6c72.
No held-out inference, quality claim or interim checkpoint selection follows.
The existing public endpoint receipt now includes this engineering follow-up.

Root free space fell from about 166 GiB at expanded 1k to 154 GiB at 4k. The
whole current study occupies 5.2 GiB, so it does not account for most of that
drop. Found 76 large regenerable pytest checkpoint/reference-copy fixtures in
eight inactive project Git worktrees, all from Oct16/17 and configured by this
project's pytest basetemp. Four active plans contain no literal or resolved
references to those roots. Same-user command/cwd checks and project/pytest FD
checks find no active consumers. Every selected file is fully hashed, owned by
this user, a regular file without symlinks or extra hardlinks, and rechecked
before unlinking. Other files in those temporary roots remain.

Two checks stopped before mutation: an unrelated systemd service denied FD
inspection, and a pt-only inventory omitted seven test-local pth reference
copies. FD inspection was restricted to project/pytest processes while retaining
same-user command/cwd checks, and the full pt/pth inventory was checked before
eviction. Both failed prechecks are recorded in the completed receipt.

Evicted 9,934,962,614 payload bytes / 9,935,429,632 allocated bytes (9.25 GiB).
Root free space was 154.12 GiB immediately before and 163.56 GiB after; concurrent
filesystem activity also affects those free-space measurements. External space
stays about 608 GiB. All active plan hashes and the live training owner remain
unchanged. Inventory, executed driver and receipt are retained under
.cache/benchmarks/old-pytest-checkpoint-eviction-20261019-v1; public summary is
docs/results/old-pytest-checkpoint-eviction-20261019-v1.json.

The trainer advanced past 4450 during these checks. Both original endpoints and
the complete quality/native review remain required. V43 remains the working
reference; SOTA, broad real superiority and 100MP/10s remain unmet/unproven.
No personal source drive was accessed. The full goal stays active.
