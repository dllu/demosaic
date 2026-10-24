# Independent retained-prediction quality review

Recorded: 2026-10-24T07:10:16-07:00 (America/Los_Angeles).

Previous goal turn was progress: pushed `36feac9` with complete eight-view
results, retained predictions and successful guarded V114/V115 CUDA starts.
This turn confirmed the exact live training/evaluation processes and continued
work without repeating a neural experiment.

Added independent NumPy64 archive metrics and a CPU audit/queue. It checks
complete report joins, shared contexts/targets, photo linear/rendered PSNR and
chroma/gradients, measured-CFA scores, color/CFA bias, carrier gain/phase/residual
and neutral-flat FFT bands. Camera masks retain the 1024-sample threshold.
SSIM and masked boundary/shadow scores retain their original implementation.
Paired photo sources receive equal weight; cameras average crops within capture,
captures within scene, then scenes equally. Bootstraps use fixed source/scene
units and do not claim training-repeat uncertainty.

The reviewer creates native 160-pixel bark/canopy noisy-Malvar/restored/exact synthetic
GT triplets with common ROI, WB/matrix and exposure. Receipts retain source,
checkpoint, conditioning, target/prediction bindings and encoded cell hashes.
PNG cells are reopened and checked, with actual viewing explicitly separate.
Future GFX/ISO100 comparisons remain nonexact references and need human review.

Two initial saved-output proof setups failed before any prediction record:
v1 output was above the frozen safety helper's workspace, and v2 attempted a
hard link across the external/internal filesystem boundary. Both source/plan/log
sets, failure receipts and partial directories remain intact. No learned work,
RAW decoding or noise regeneration occurred. A fresh v3 proof writes inside its
own frozen work tree. The public archive now handles EXDEV with an exclusive
byte-preserving copy; other link errors still fail and originals stay intact.
Existing same-filesystem color predictions remain hard-linked.

Actual source-frozen proof completed 17 genuine retained observations: two fitted
Small photos, four Tiny/Small adverse-camera predictions, eight V111 carrier/flat
observations and three V111 color cases. Maximum photo PSNR discrepancy is
.0000021 dB, camera/color fields agree exactly, and carrier/flat differences are
below 1.7e-14. It imports no Torch and runs zero model/encoder calls, optimizer
updates, noise regenerations or RAW decodes. This is an engineering proof using
existing outputs, not a new model-quality experiment. Actually viewed all six
native cells in its two bark/canopy triplets: coarse bark structure survives;
faint grain and canopy leaves remain soft. Separate native-view receipt records
that observation without changing the completed numerical proof.

Thirty-two focused archive/audit tests pass in 1.55s. All six changed/new Python
implementation/test files pass Ruff. Fourteen frozen plan guards pass, including
the original numerical/audit/training/evaluation sources and the new proof/queue.
No original training/evaluation source, parent, budget or mutable model selector
was changed. V112 remains selected.

New independent-review owner 925140/1792851360.58 is confirmed live, waiting
without children behind exact endpoint evaluator 868302/1792848232.8. It starts
only after all eight stages finish and that owner exits successfully. It will
independently check 28,380 numerical observations, reuse existing V112/stronger
RawNIND controls and prepare two triplets per new endpoint. It needs 8GiB RAM
and 2GiB output space; no CUDA, Torch import, automatic retry or recommendation
change. Current training owner 867877/1792848017.25 remains live; at verification
2026-10-24 07:18 PDT, V114 has logged step 3900. Both waiting controllers have no
children. Trained V114/V115 quality is still pending; broad real-camera
superiority, faint-detail recovery and the 100MP/10s target remain open.

[Current archive/audit guide](../docs/quality-prediction-archive.md) ·
[Proof, source/failure boundaries and live queue receipt](../docs/results/v112-independent-archive-audit-queued-v1.json).
Private sources/evidence: `.cache/current-quality-20261023-v1/archive-audit-proof-v{1,2,3}/`
and `V112-continuations-independent-audit-v1/` under the same cache parent.
