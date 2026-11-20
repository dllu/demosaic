# Check weak detail with an exterior Bayer phase

Recorded: 2026-11-20T04:49:10-08:00 (America/Los_Angeles).

The [phase extent study](../docs/local-phase-extent.md) separates estimation
of a weak waveform from the local evidence for keeping its correction. It
uses four independent frequency and phase donors and compares 16-pixel
station scores with near, wide and coarse-color-guided pooling. The
calibration uses the original 32 source photos. Two earlier 24-photo panels
and 32 new source-disjoint photos use the frozen thresholds and weights.

At equal recovered contrast, keeping the local check lowers added gap
luma RMS by 0.073, 0.212 and 0.122 DN16 on the three evaluations. One
background accounts for 97% of the new panel's mean and the interval
reaches zero. Uniform scaling gives nearly the same result as wide or
coarse-color-guided pooling on those new backgrounds. The practical
benefit of the local check is strongest on a few large errors.

The `weak-phase-guard` crop API matches the selected replay within
0.002 DN16 peak over 384 synthetic and eight standing RAW crops. Both
native comparison families are complete, including all 12 boards for
[the main GFX scene](../docs/gfx-qualitative.md) and [the cab mesh](../docs/gfx-green-mesh.md).
The coarse fence preserves crossings, and the sky, building and foliage
reproduce Local 50k. Both right cab profiles use the uniform fallback
because the exterior phase is inconsistent. Four exact-target triplets
were viewed, including the largest prior and new gap differences.

This is a frozen-checkpoint crop experiment. The fixed panels in the
[PSNR history](../docs/performance-history.md) remain outside its scope.
[Receipts and code bindings](../docs/results/local-phase-extent-v1/publication.json).
