# Estimate spatial Bayer color phase on held samples

Recorded: 2026-11-20T03:07:13-08:00 (America/Los_Angeles).

Fit constant and affine color-specific quadratures relative to the
measured green phase. The spatial field instead fits each color
checkerboard in disjoint 24-pixel nodes, smooths the complex
coefficients, and checks its prediction on the complementary samples.
Replacing every held sample leaves its fitting-side field identical
across the eight CFA-position and fold tests.

On the fresh stronger-chroma ISO1600 set the field with a positive
central check delivers in 78 of 208 suppressed windows. Signed
response gains 1.117 points and local RGB RMS falls 0.474 DN16 with
equal gap RMS. One scene drives the stronger ISO6400 gain. Earlier
weak panels show little transfer. The clean-target audit gives the
affine basis higher capacity than planar even where noisy fits fail.

Wider competition against neutral admits some supported color outside
the suppressed windows. On the real coarse fence it changes 19 color
windows by 2.28 DN16 RGB RMS across the crop. The standing sky,
building, foliage and all four fine cab outputs match the local
conditional fit. Both exact changed crops and both protected GFX
families were viewed at native size.

[Report](../docs/cfa-relative-phase.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).
