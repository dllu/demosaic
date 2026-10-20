# Defer speed work and return to V43 data quality

Recorded: 2026-10-20T11:24:28-07:00 (America/Los_Angeles).

The user redirected the next stage toward quality: keep V43's architecture,
use the larger available Commons corpus, visually curate difficult sources,
reduce blurring augmentation and add low-contrast detail. Speed work is deferred.

The unchanged original precision-worker replay finished before that request.
Its V43/GFX half-precision outputs still exceed the historical parity limit;
the wrapper alone does not explain the difference. The cause remains unknown.
[The archival receipt](../docs/results/mature-original-worker-replay-v1.json)
retains output comparisons and exact timed-output checks without claiming
a speed or quality result. A separate fixed-backend pilot was prepared but
**never launched**; its settings tests are CPU-only checks.

The V43 training-source screen is running against the available 88,508 Commons
training sources. It uses the original checkpoint, fixed center crops, FP32 and
two fixed noise conditions. High loss only selects candidates for visual review.
It does not automatically exclude sources. The initial 31-source review retains
27 sources and withholds four; larger native views resolved the soft/noisy cases.
Originals and historical manifests remain unchanged. No new model has trained.

The quality-first plan and forthcoming results belong in
[the training study](../docs/quality-first-training.md). The README and experiment
index are being shortened, with detailed history retained in an archive and a
source-bound PSNR-versus-version plot. Diary filenames now use local time;
the separate correction commit preserves all historical entry bodies.

