# Phase-paired Bayer donor power

Recorded: 2026-11-19T19:30:55-08:00 (America/Los_Angeles).

Kept the 32-pixel dense donor atlas and frozen Corpus 100k EMA.
Validated pooled sine/cosine power in disjoint donors and took the
delivered phase from the query innovation. The on-grid invariance
check passes on all four physical Bayer layouts.

At the wire-flat calibration, nominal left-cab change rises
from 0.287 to 0.463 DN16 RGB RMS. Both measured frequencies gain
projection even at equal added RGB RMS. The ×4 and ×16 crops show
incomplete crossings. Sky stays smooth. Both GFX families, both
cab priors and both JPEGs were viewed.

At recovered short-wire response matched to 40.547%, false projection
falls 0.246 DN16 and exact-flat error rises 0.137 DN16. At the fixed
flat budget, the phase-paired fit recovers less short detail than
the dense cosine prior. The independent natural-photo errors still
favor Corpus 100k without the correction. The scoped frozen-EMA
study leaves the broad model history at the existing measured results.

[Report and native exact targets](../docs/scene-phase-power.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine mesh map](../docs/gfx-green-mesh.md) ·
[Fixed-panel history](../docs/performance-history.md).
