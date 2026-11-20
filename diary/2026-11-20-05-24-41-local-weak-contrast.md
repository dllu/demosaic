# Recover more contrast with a separate weak phase check

Recorded: 2026-11-20T05:24:41-08:00 (America/Los_Angeles).

The [weak contrast report](../docs/local-weak-contrast.md) separates weak
admission from the amount of contrast the posterior delivers. The cap
engages in one of 1,634 admitted windows across the calibration and four
evaluation panels. Setting full amplitude without a phase check gains
2.869 points on 48 new sources and raises mean gap luma from 0.046 to
0.166 DN16. The initial strength ramp is the main source of attenuation.

The calibrated `weak-phase-contrast` crop option keeps the same windows,
uses full fitted amplitude where donor phase is reliable, and applies
the original local support taper. Its nominal improvement is 0.921
weak-response points and 0.694 DN16 lower intact weak error. Added gap
luma rises 0.010 DN16. At equal gap change, the gain is 0.401 points.
All 48 unplanted natural groups reproduce their parent with authentic
context. Incorrect exterior RAW can still add texture. The weakest
half gains 0.234 points with very little gap change.

Numerical and native reviews are complete. The API matches the research
fit within 0.002 DN16 on 576 synthetic and eight real crops. The
[main scene](../docs/gfx-qualitative.md) retains smooth sky and connected
coarse crossings. Both [fine cab views](../docs/gfx-green-mesh.md) retain
the fixed-guard fallback and incomplete crossings. Two exact-target
triplets show the packaged output in the same native coordinates.

The crop study uses frozen weights. The fixed broad benchmarks in the
[PSNR history](../docs/performance-history.md) fall outside its scope.
[Receipts and source bindings](../docs/results/local-weak-contrast-v1/publication.json).
