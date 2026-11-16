# Refine A-only edge geometry and complete shared-edge training

Recorded: 2026-11-16T02:02:45-08:00 (America/Los_Angeles).

The exact shared-edge training process completed all1,000 rows:900 noisy updates,
100 ADC skips. Its controller audited every checkpoint's identity, learning
rate, frozen-state hash, Adam clock and finite head/EMA tensors. Raw evaluation
completed all822 original inputs; EMA evaluation is live. The raw endpoint has
slightly lower blank/quiet error and lower mesh projection than V200 raw; native
inspection and complete raw/EMA interpretation remain pending. No recommendation
changes. [Completion receipt](../docs/results/shared-edge-training-completed-v1.json).

Added three A-only9×9 angle/offset refinement grids to the analytic nuisance fit.
The NaN-heldout test still proves discovery excludes validation values. Default
affine/step predictions, variances, selections and scores exactly reproduce an
archived-source replay. Both original and refined arms use the same source/noise
seeds;1,792 affine-control rows reproduce exactly across7,168 total fits.

An additional off-grid-edge/two-wave family measures the weaker direction
explicitly. At calibration-only thresholds9.055919065 versus2, both arms have
0/384 observed test-null activations; weaker-direction gain rises2.39%→56.99%,
and exact increment error falls65.01→27.71DN16. Paired source-cluster intervals
and fixed-threshold curves are archived. Already represented edges show a small
response/error regression. These restricted sine/step results do not prove real
camera safety or a neural model gain.

Published two native96 exact-GT RGB triplets and grid/refined comparison boards,
with exposure4/contrast1, identity WB/matrix, exact source/noise fingerprints and
an analytic configuration hash. RGB evaluation is checked against every measured
CFA prediction before rendering. Both boards were actually viewed. All old
receipts and sources remain archived byte-for-byte; full new fit receipts are
gzip archives with exact decompression checks.36 focused tests and Ruff pass.

[Full analytic report](../docs/withheld-cfa-edge-refinement.md).

