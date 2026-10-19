# Commons cache recovery after the memory guard

The local download completed all 1,188 originals. Its preparer stopped at the
memory guard, retaining **771 manifest-recorded 4× arrays**. A new frozen worker
waits for the exact GPU-review/CPU-closure owner to exit successfully, then
recovers both cache scales onto the external SSD. A fresh archive handoff waits
for successful preparation.
[Verified waiters, source bindings and actual fixture](results/commons-local-memory-recovery-queue-v1.json).

The recovery preserves the failed plan, logs, partial manifests and arrays.
It checks the original producer source, partial recipe and manifest. Each
reusable array must retain its source attribution, canonical identity/path,
SHA-256, uint16 HWC shape and recipe. It makes a separate atomic copy with the
same hash; source arrays stay untouched. Unrecorded orphans are regenerated.
A corrupt recorded array stops recovery. The unchanged ingestion operator
reuses verified copies and generates the remainder. Full original/cache checks,
the one-code 4×→area2 versus direct8× bound and protected-scene/GFX screening
still apply. All 44 training-core files match the failed producer.

Production uses one CPU worker, hidden CUDA and a **608 GiB external reserve**.
After review/closure exits, it requires at least 48 GiB available RAM for 60
continuous seconds; the 24 GiB per-source guard remains. The handoff reconciles
completed local originals before the unchanged bounded downloader resumes:
two workers, .25 request starts/second, 608 GiB reserve, 10,000-file limit and
the existing shared archive lock.

Twenty focused tests pass, including corrupt bytes/metadata/source, escaping
paths, low RAM and failed/changed dependencies. An actual frozen two-source
fixture stopped at an injected guard after one real array, then recovered both
scales on the external SSD. One cache was reused without decoding; the source
remained unchanged. All 1,328,802 area samples agreed within one code, and
protected-scene checks completed. The actual waiter created no outputs and
loaded no Torch/CUDA libraries before its controlled predecessor exited.
This is ingestion engineering evidence, without a corpus or quality conclusion.

At the published observation both production waiters are live and childless,
without Torch/CUDA mappings. No production cache copy, reconciliation or broader
download has begun; the archive index matches the old handoff snapshot.

- Preparation: `/mnt/external/demosaic/commons-qi-local-preparation-memory-recovery-20261019-v1/`.
- Handoff: `.cache/commons-archive-handoff-memory-recovery-20261019-v1/`.
- Actual fixture: `.cache/benchmarks/commons-local-recovery-preflight-20261019-v1/`.

Check current status/logs and PID plus creation time before acting on a dated
receipt. Failed guards preserve the new run too. Sources remain quarantined or
reserved. Independent duplicate/content/known-series review, matching scale
membership, holdout handling and a separate frozen data recipe remain required.
The standing GFX scene and siblings stay out of training.
