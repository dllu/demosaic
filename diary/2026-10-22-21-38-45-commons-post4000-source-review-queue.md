# Queue complete incoming-source contact sheets with an explicit reserve

Recorded: 2026-10-22T21:38:45-07:00 (America/Los_Angeles).

Prepared all-source visual review for the3809 new eligible arrivals. The renderer now accepts an explicit integer reserve>=256GiB, retaining its548GiB default; production uses288GiB. Complete selected-source coverage, all cache SHA/header/attribution checks and rejection of temporary manifests remain unchanged. Eight focused tests pass, including invalid budgets before resource access, exact/one-byte-short RAM/disk boundaries, the original default, partial-manifest rejection and incomplete-source coverage. Ruff/format checks pass.

A genuine completed two-source cache fixture ran the actual frozen queue and renderer. Its output PNG matches the prechange renderer byte for byte; both source thumbnails were viewed. Both frozen production source files exactly match the executed fixture. The new queue is live behind the exact preparer, waiting for finalized4x manifest/errors/summary with zero failures. It will render39 source sheets while8x may still prepare, without admission or quality approval. Four-hour producer wait, one-hour render bound, five-hour timeout and no retry. The original producer and training/evaluation/full-frame jobs remain untouched.

Root: `/mnt/external/demosaic/commons-post4000-contact-queue-20261022-v1/`. Queue SHA256: `a27b96b85d00d5892bd2e27942caa101216049307642755d8f3a2062667c9bfb`. No new-arrival thumbnail has been reviewed yet; the two viewed engineering sources belong to the earlier completed fixture. [Executed fixture and live owners](../docs/results/commons-post4000-contact-queue-v1.json).
