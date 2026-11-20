# Separate wide carrier estimation from center validation

Recorded: 2026-11-20T01:08:49-08:00 (America/Los_Angeles).


Separated carrier fit, validation window and delivery width. Fitting
and checking one green at a time over 64 pixels and delivering to
the central 32 matches the existing wide fit on the exact optical
panel. Verifying the same coefficients on the held center alone
drops weak-response gain from 4.365 to 0.213 points at the inherited
threshold. Checks across all four Bayer layouts left fitted
coefficients unchanged when held samples changed.

The exploratory threshold of three recovers 1.927 points over
Local 50k and activates zero of 56 exact-flat crops. At the
earlier-panel response match it reduces continuing-strand RMS
2.650 DN16 versus scaled broad verification on the other 24
sources. The threshold of 1.5 admits 37 flat crops and shows
worse gap errors at comparable response. Both cutoff panels reuse
the previous optical sources.

Viewed four exact native triplets and both standing image families.
The center check at threshold three keeps the coarse fence and
makes the right cab diagonals clearer than at threshold six.
Fine cab crossings and green-gray splotches remain. This is an
inference-only crop study on the frozen Local 50k EMA.

[Report](../docs/local-center-guard.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine mesh map](../docs/gfx-green-mesh.md) ·
[Parent benchmark](../docs/scene-50000-cameras.md).
