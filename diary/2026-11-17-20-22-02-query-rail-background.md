# Explain rail boundaries inside the RAW query

Recorded: 2026-11-17T20:22:02-08:00 (America/Los_Angeles).

The matched-shape score removes the held-out amplitude penalty.
Per-fold null-space projection also removes correlations with
the fitted nuisance and competing guide. Both raise ISO400 quiet
RMS at the original scale. Matching the predictive quiet RMS
lowers full-frame weak response from 4.80% to about 1.77% even
though all three arms use the same guides and delivery family.

Two parallel query boundaries reduce forced-guide rail error
from 7.29 to 0.79 DN16 and retain 4.80% weak response with the
full-frame guides at the refined single-step quiet limit. Adding
the stricter gate further reduces rail error, with less wire
response. The two-boundary fit also removes most false building
color under the fixed spectral guide. I viewed both native
GFX families. The cab crossings remain missing.
[Report, native crops and receipts](../docs/query-rail-background.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine green mesh](../docs/gfx-green-mesh.md).

The full-corpus schedule passed 66,400 updates. The latest
quality review remains at 50k. This component replay uses
archived EMA predictions and changes no standard panel scores.
[Training milestones](../docs/full-corpus-scaling.md) ·
[Standard panel coverage](../docs/performance-history.md).
