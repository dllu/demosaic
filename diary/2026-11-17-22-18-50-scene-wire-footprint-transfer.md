# Test wire footprints with whole-image frequency proposals

Recorded: 2026-11-17T22:18:50-08:00 (America/Los_Angeles).

Replayed the two saved ordinary-wire geometry panels over V143 with the
whole-image frequency proposals, plus exact centers on the main panel.
The earlier sinusoidal footprint gains do not repeat on these profiles.
The fundamental loses response even with uniform support. With eight
knots, tapering increases ISO400 increment error on both panels. A veto
using the companion's own held-out RAW gains largely restores the
uniform result. It accepts no forced-guide rail-only taper and keeps
two of eight prior ISO400 sinusoidal two-direction observations.

Inspected both synthetic triplets and both GFX scene families. The sky
remains exact to V120. The eight-knot taper preserves the coarse lattice
and leaves all four cab crops at their conditioned V120 pixels.
Spectral foliage gains a slightly stronger correction without clear new
leaf detail. This was a CPU component replay with existing weights.
[Results and evidence](../docs/scene-wire-footprint.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md) ·
[Full-model score history](../docs/performance-history.md).

The first camera comparison compared a tuple in the live trace with
a list in its saved JSON. Replaying with normalized traces found
identical fundamental output arrays. The failed log and corrected
receipt are preserved. All 120 focused tests passed.
