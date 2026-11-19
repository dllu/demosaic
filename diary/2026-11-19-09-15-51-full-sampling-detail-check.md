# Opposite-view detail checks without Bayer interpolation

Recorded: 2026-11-19T09:15:51-08:00 (America/Los_Angeles).

Ran the existing Corpus 100k EMA on full-lattice plus/minus views
with locally estimated shot/read variance. On 48 held-out photos at
ISO6400, opposite-view checking reduces own-view increment error
0.31 DN16. Above full-input Corpus 100k, the positive check adds
0.018 response points and raises increment error 0.014 DN16.
Gaussian validation decorrelates the pair with known noise. Simulated
near-white clipping gives substantial anticorrelation.

A response-matched 32-pixel boost visibly adds halos in the standing
foliage and fence. Moving the gain into the measured fine band retains
coarse structure but leaves a detail tradeoff. The half mix reduces
flat RMS 0.11 DN16 and raises increment error 0.65 DN16. Viewed two
same-input exact-target triplets and all eight standing crops. The
unconfined average softens the cab diagonals and no candidate restores
the missing crossings. Broad scores continue to refer to the original
Corpus 100k EMA.
[Report](../docs/full-sampling-detail-check.md) ·
[Main review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Performance history](../docs/performance-history.md).
