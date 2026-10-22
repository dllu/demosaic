# Held-out bark feather canopy and fur comparisons

Recorded: 2026-10-22T12:45:17-07:00 (America/Los_Angeles).

Added a four-source natural-detail comparison for the current V84 architecture:
pale bark grain, white egret feather texture, forest canopy/haze and gray fur.
Viewed ten clean native256 contexts and their native160 centers before selecting
these four and before viewing their new model outputs. They are original
indices124/200/320/392 of the fixed full427 validation dataset, seed42.
Exact IDs are absent from the active 88,484-source training cohort; this does
not establish complete near-scene independence.

`configs/heldout-fine-detail-v1.json` records all source attributions, original
cache coordinates and clean-context hashes. The contexts cover mixed contrast,
including subtle fine structures; they were not selected as globally flat
images. Native display ROI is [48,48,160,160]; numerical metrics use the larger
[8,8,240,240] interior. Keep those scopes distinct.

`scripts/report_heldout_detail.py` freezes numerical source and caches 12 CPU
observations: four contexts × ADC-only/ISO100/ISO12800 × RGGB. These are newly
generated CPU noise draws, shared exactly across models, not replacements for
the original full-panel CUDA results. The runner uses CPU FP32, verifies cached
inputs after each prediction and model hashes before/after, and writes standard
native triplets with complete source/checkpoint/noise/display metadata.

Prepared a fresh v2 input plan after adding copied-selection and license binding:
`.cache/current-quality-20261022-v1/heldout-detail-inputs-v2/plan.json`.
The unused v1 preparation remains separate. Future comparisons use v2's copied
worker. V84 final20k and RawNIND with input-only CFA-channel gain completed
24 predictions. Actually inspected all three native comparison boards, totaling
48 native160 cells and representing 24 triplets. V84 is substantially sharper
than RawNIND at low noise; high-noise white plumage, canopy and fur remain
smoothed. This is a V84 diagnostic, not a newly trained improvement.

Published `docs/heldout-detail.md`, current per-condition galleries and
`docs/results/heldout-detail-V84-reference-v1.json`. The receipt binds immutable
private reference boards and unchanged per-model source triplets. Current
gallery paths can gain useful new models without rewriting this evidence.
Linked the gallery from current-model, quality-first-training and docs/index.

Validation: actual full reference run, Ruff check/format, 59 bound artifact
references, all 48 comparison-cell byte hashes/native dimensions and updated
documentation links passed. Frozen training, evaluation, full-frame and new
detail-input plans all pass their input/source guards. No numerical training or
primary-evaluation source was changed. V100 is still training (step9600 at the
latest check); V101 and the existing evaluation/full-frame queues remain live.
