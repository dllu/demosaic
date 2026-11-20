# Ring phase prior for weak Bayer detail

Recorded: 2026-11-20T03:54:53-08:00 (America/Los_Angeles).

## Decision

Expose the ring-phase estimator as an opt-in crop method. The calibration
picks log-odds −6 per direction and inclusion cutoff 0.20. On 24 new,
source-disjoint ISO6400 photos the fit gains 0.506 weak-response points
over the combined check and adds 0.026 DN16 false weak projection to
the exact gaps. The response interval spans zero. At the earlier
response match the continuing-strand error rises 4.353 DN16. Supplying
exact frequencies changes the fresh response by only 0.021 points.

The main scene's sky stays smooth and the coarse crossings remain visible.
One of the nominal right cab directions becomes more prominent, with
incomplete crossings near the post and variation through the mesh.
The two noise priors and JPEGs were viewed at both display exposures.

## Record

The method lives behind `method="ring-posterior"` in the native crop API.
It reproduces 288 fresh and eight camera crop results bit for bit. Both
frozen parent EMAs are retained. Numerical review and native comparison
of two exact target triplets, both standing RAW families and the
response tradeoff are complete. The two fixed broad camera panels and
full photo scoring are outside this component scope.

[Report](../docs/local-bayer-presence.md) ·
[Inference usage](../docs/usage.md) ·
[Main GFX100S review map](../docs/gfx-qualitative.md) ·
[Fine green mesh review map](../docs/gfx-green-mesh.md) ·
[Fixed panel coverage](../docs/performance-history.md) ·
[Publication and frozen hashes](../docs/results/local-bayer-presence-v1/publication.json).
