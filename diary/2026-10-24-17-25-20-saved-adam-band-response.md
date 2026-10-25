# Check Adam response to retained faint-detail gradients

Recorded: 2026-10-24T17:25:20-07:00 (America/Los_Angeles).

V116 is running its original20k fine-source/reference-mask trial. Its original
worker PID1583366/creation1792886699.3 remains live and logged875 updates at the
start of this turn, with finite losses. No running source, recipe, optimizer,
checkpoint parent or queue was changed. V114 remains the current general model.

The earlier normalized-band diagnosis measured raw parameter-gradient alignment,
which is not an Adam update direction. Reused the two original retained V112
faint/high-noise training cases to check the fresh AdamW gradient component,
with norm1 clipping and epsilon1e-8. Both real gradient norms are below1. The
first bias-corrected component is−g/(abs(g)+epsilon), per unit LR; common weight
decay and accumulated moments are outside this calculation. No checkpoint/model
is loaded and no new forward/backward or restoration update occurs.

The Adam-component correction cosine changes−.023574→−.024727 in the new-photo
case and+.014318→+.011085 in the reviewed ROI. The band addition lowers alignment
in both. The corresponding direction-dot changes are−1.204297 and−4.996482 per
unit LR. First-order signs agree with the earlier raw-gradient concern despite
different magnitudes. Largest adverse module contributions differ between the
two cases; this does not identify one robust parameter-group intervention.

All534 original FP32 gradient arrays pass hashes/shapes and reproduce the old
per-layer Gram values. Two unrelated Torch64 zero-parameter AdamW fixtures
check clipping and near-epsilon behavior, maximum discrepancy2.22e-16. Those
two fixture steps are explicitly separate from zero restoration-model updates.
Torch RNG stays exact, no CUDA initializes, and no observation or RAW is read
or generated. Runtime is5.14s on CPU with two Torch threads/nice10.

This is an exploratory local response on the two previously retained V112
examples, not a new V114 measurement, mixed-batch/late-Adam response or observed
image-quality result. It does not justify adding the loss to V116; that original
data comparison continues unchanged. A later loss experiment still requires
actual training, complete panels and native noisy/restored/GT plus GFX review.

The executed source initially had an unsorted import block. Preserved that
frozen file and plan/log/result; only standard-library import ordering changed
in the public helper for Ruff. Non-import ASTs match exactly, and no analysis
or model work was repeated for lint. Ruff now passes.

[Bound plan, results and scope](../docs/results/saved-Adam-band-response-v1.json) ·
[Current loss diagnosis](../docs/contrast-normalized-band-supervision.md).

