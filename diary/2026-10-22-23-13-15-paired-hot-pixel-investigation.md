# Trace recurring green-pixel pairs behind residual roof specks

Recorded: 2026-10-22T23:13:15-07:00 (America/Los_Angeles).

Traced the user's residual roof specks through the existing RawPuppy geometry
back into normalized Bayer samples. The cyan dot is a green same-phase pair at
(1128,4281)/(1128,4283), at 1.0/.50014 in DSCF3842 and approximately 1.0/.503
across three other cached captures. A second dot is a diagonal pair in the two
green phases. The isolated maximum-neighbor rule lets the first pair hide each
other; the immediate-neighbor light guard falsely protects the second pair.
The photos establish recurrence, not the physical cause.

Added opt-in `--hot-pixel-clusters`, implying `--hot-pixels`: tolerate one
contaminated same-phase neighbor, require different-color light corroboration,
and preserve continuing lines. The initial permissive prototype clipped four
pixels at narrow green-line ends; the continuation guard fixes that regression.
Defaults retain the earlier isolated behavior, whose complete DSCF3842 count
and coordinate hash reproduce exactly. Forty-four focused tests, Ruff and
whitespace checks pass.

The optional detector changes 6,235 sites versus 3,229 in DSCF3842. Matched V101
CPU 512 contexts remove both identified specks while retaining the inspected
blue-lit façade control; all three native 160 triplets were viewed. No exact
GT or quality-population score is available. Larger/mixed-color clusters and
unresolved pure-color lights remain ambiguous. A weaker red/green pair in the
same screenshot remains unchanged and is not confirmed by recurrence.

The [case writeup](../docs/hot-pixel-clusters.md) records coordinates, noise,
checkpoint hash and limitations. Private source values, native PNG/float crops
and mapping/neighbor-rule receipts stay in the requested composites directory.
This turn investigates and tests the correction; it does not replace the
existing full DNGs/JPEGs or alter the concurrent main checkout.
