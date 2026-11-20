# Test wider Bayer color support and independent phase

Recorded: 2026-11-20T02:54:29-08:00 (America/Los_Angeles).

Pool disjoint Bayer-node sufficient statistics in an equal-area
isotropic kernel or a 28 × 10 pixel Gaussian along the strand.
The pooled gate retrieves no additional signed color in 80
suppressed windows across the retained and fresh optical panels.
A fit-side negative-polarity mask and a positive-only central
threshold reproduce that result. Gaps and controls retain the
local conditional outputs.

The exact post-optics color waveform passes both held checks
in 16/48 retained and 10/30 fresh ISO1600 windows. It passes
0/2 in the fresh ISO6400 panel. That diagnostic uses the clean
target to supply its phase and finite support.

Independent sine and cosine fits on red and blue recover a
single additional red window on retained ISO6400 and two on
fresh ISO1600 with the relaxed center check. The fresh mean
signed response gains 0.083 points and remains negative.
Fresh ISO6400 and all eight standing GFX crops reproduce the
local conditional pixels. The two changed ISO1600 triplets
and both standing families were checked at native size.

[Report](../docs/cfa-directional-chroma.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).
