# Fit the weaker Bayer direction separately

Recorded: 2026-11-20T04:11:56-08:00 (America/Los_Angeles).

## Decision

Add the calibrated weak-only posterior as an opt-in crop method. The
distant donors provide frequencies, and their amplitude rank is
ambiguous on all 32 calibration photos. Both green lattices agree on
the weaker local direction in 158 of 160 exact-target draws.

The corrected strength sweep blends only the weaker update over the
combined check. On 24 new validation sources this recovers another
1.807 percentage points and lowers intact weak RMS 1.323 DN16.
Continuing-strand error changes 0.001 DN16 and false weak projection
rises 0.084 DN16. The earlier numerical sweeps and their different
blend convention remain bound in the archive. The phase-aligned tested
arm has less recovery and a large uniform outlier on an earlier panel.

## Record

The new option changes the right cab by 4.94 and 5.48 DN16 RGB RMS
under the two fixed priors. The left returns the combined fit when the
directions are ambiguous. The standing sky remains smooth and the
coarse fence keeps its crossings. Both photo families and two native
exact triplets were viewed. The packaged method and experimental
results agree to 0.002 DN16 peak across 296 crop comparisons.

The study reuses the Local 50k and V120 EMAs. Evaluation is complete
within the crop scope. Fixed photo and known/unseen camera scores
use their existing endpoints.

[Experiment report](../docs/local-conditional-posterior.md) ·
[Crop option](../docs/usage.md#repeating-mesh-crops) ·
[Main GFX100S review map](../docs/gfx-qualitative.md) ·
[Fine mesh review map](../docs/gfx-green-mesh.md) ·
[Fixed panel history](../docs/performance-history.md) ·
[Publication](../docs/results/local-conditional-posterior-v1/publication.json).
