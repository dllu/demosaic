# Finite wire footprints and fourth corpus pass

Recorded: 2026-11-17T21:37:29-08:00 (America/Los_Angeles).

Changed the wave basis inside the two crossed RAW folds while leaving the
screened edge nuisance, frequencies, gate and delivery estimator fixed.
Replayed 16 archived pairs and 16 independently drawn pairs. At the fresh
ISO400 operating point a supplied exact ellipse and fundamental phase fit
raise weak response from 0.86% to 13.77% and lower increment RMS from
6.72 to 5.91 DN16. Widening both radii keeps 12.14% and moving the center
40 pixels leaves 0.32%. ISO6400 error increases even with the matched
ellipse. On 48 forced-guide flats and rails, the broader fundamental fit
lowers false complex-rail RMS but raises straight-rail RMS relative to
the uniform eight-knot baseline.

Reviewed two synthetic triplets and both GFX families at native size.
The real replay uses uniform support. The fundamental basis halves the
spectral building correction, preserves the coarse fence and returns the
sky and four cab crops to V120. The fine cab reference crossings are
still missing. The study completes numeric and native review without new
training. [Report and evidence](../docs/wire-envelopes.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

The first archive replay needed one additional dynamically imported
script in its frozen sources. The failed logs and corrected snapshot
are retained. All 134 focused tests passed.

Verified the fourth pass through all 90,778 ordinary sources at step
68,269 and fifth-visit crop coverage at step 72k. This is source and
conditioning evidence. The latest completed native-image review is
still the retained 50k checkpoint.
[72k coverage audit](../docs/full-corpus-scaling.md#fourth-photographic-epoch-and-the-72k-prefix) ·
[Current score coverage](../docs/performance-history.md).
