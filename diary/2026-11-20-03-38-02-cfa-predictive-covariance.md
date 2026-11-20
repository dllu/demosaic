# Noise-weighted Bayer checks for weak color detail

Recorded: 2026-11-20T03:38:02-08:00 (America/Los_Angeles).

## Decision

Per-pixel noise weights have a useful effect in the controlled large-gradient
test with exact frequency. At ISO6400 the nominal gate passes 66/384 weak
targets compared with 34/384 under common variance. The null fixtures pass
zero times in both arms. The extra predictive covariance delivers practically
the same effect as diagonal weighting.

The 16 fresh source-disjoint mixed-illumination scenes show far less transfer.
On the 12 signed ISO1600 cases, the matched affine gain is 0.073 response points
with an interval spanning zero. The signed mean remains negative. The new
weights deliver no additional color at ISO6400 or on either standing
GFX100S family. This leaves the evidence for the earlier field stronger
as an overall comparison.

## Record

The existing Local 50k and V120 EMAs provided the parents. Numerical evaluation
and native viewing cover two changed exact-target crops, all four main
GFX100S crops and both cab ROIs at both priors and both displays. Training,
fixed 427-photo scoring and the fixed camera panels were outside this
inference-only comparison.

[Report](../docs/cfa-predictive-covariance.md) ·
[Main GFX100S review map](../docs/gfx-qualitative.md) ·
[Fine green mesh review map](../docs/gfx-green-mesh.md) ·
[Fixed panel coverage](../docs/performance-history.md) ·
[Publication](../docs/results/cfa-predictive-covariance-v1/publication.json).
