# Local sensor support for mesh transmission

Recorded: 2026-11-18T13:05:37-08:00 (America/Los_Angeles).

Tested whether repeated mesh needs a contrast model that accounts for the
photographed background. The four synthetic roles use the same geometry on
24 natural photo backgrounds. Relative to the affine fit above Corpus 100k,
local transmission lowers high-noise transmissive wire RMS from 286.31 to
282.55 DN16 and lowers added gap variation from 17.35 to 16.14 DN16. With
global support the added gap RMS reaches 31.11 DN16. Affine still has lower
error on the additive wires and at ISO400.

Viewed the exact-target synthetic comparisons and both standing GFX families.
The local check fades some regular stripe on the cab and leaves the existing
adjacent-donor crossings mostly as they were. Fine crossings remain
incomplete. The overcast sky, foliage and building retain parent pixels.

This study uses frozen EMA parents with an analytic correction, so there is no
new training checkpoint or entry in the fixed photo and camera score history.
[Technical report](../docs/mesh-background-transmission.md) ·
[Publication manifest](../docs/results/mesh-background-transmission-v1/publication.json) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine GFX cab review map](../docs/gfx-green-mesh.md).
