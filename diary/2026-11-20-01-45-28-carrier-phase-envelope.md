# Test local phase slopes against matched Bayer fits

Recorded: 2026-11-20T01:45:28-08:00 (America/Los_Angeles).


Compared constant, amplitude-only and complex affine envelopes
with the combined 64/32-pixel RAW check. The 32 newly selected
photo backgrounds give 12 calibration and 20 confirmation sources.
Straight and warped captures share the observed exterior donors.
Altering the held green lattice leaves fitted coefficients
bit-identical in all four CFA layouts and at odd ROI origins.

On the warped confirmation fields, adaptive complex slopes recover
0.183 more weak-response points than the fixed combined fit and
lower intact fundamental error by 0.116 DN16. At comparable weak
response the continuing-strand RMS rises 1.509 DN16. The complex
fit admits two edge-only and one flat-core recipient out of 40
per role. The exact synthetic phase shift gains 0.920 points in
the separate weak-only diagnostic and increases passing windows
from 129 to 209 with no control activations.

Viewed both exact native triplets and both complete GFX families.
The nominal adaptive variants change four direction windows on the
left cab and three on the right, with incomplete intersections.
This trial uses frozen Local 50k and V120 EMAs.

[Report](../docs/local-carrier-envelope.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Cab mesh review map](../docs/gfx-green-mesh.md).
