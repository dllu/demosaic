# Local Bayer evidence with a separate exterior phase guide

On the optical development scenes at σ 0.85, increasing the local
readout window from 32 to 64 pixels raises weak-strand detection
from **49.2% to 90.2%** when phase is estimated outside the query.
The signal-poorest half rises from **37.8% to 82.8%**. In this controlled
setting, much of the weak signal is still present in the Bayer samples.
How much a detector can use depends on its window size and phase estimate.

## Setup

The 32 photos come from the earlier [optical development replay](sensor-optical-transfer.md).
Each source supplies strong-only, strong-plus-weak, exact-flat and
exterior-only roles. For actual strip and ellipse gaps, the test uses
the same hypothetical weak phase inside the gap as a false-activation
control. The 128 × 128 score region and three-pixel gap erosion match
the optical replay. The smaller windows are nested inside it. The
32-pixel window is positioned to retain the most intact pixels using
the clean support mask.

The exact-template diagnostic uses the clean weak contrast in camera
space and either the exact underlying background or a plane or
edge-and-strong-strand nuisance fit. The known-background comparison
subtracts the exact null mean and shows the amount of signal available
with both clean quantities supplied. In the fitted versions, half the
2 × 2 Bayer cells fit nuisance coefficients for each Bayer phase.
The fixed template is scored on the other half. The final linear score
combines the two directions and includes their covariance.

The exterior-phase variant is given the frequency, score masks and
edge/strong-direction geometry. It gets the weak phase and per-phase
shot-variance scale from the exterior-only Bayer observation in a
separate annulus of the 512 × 512 scene. The synthetic annulus has a
strong coherent version of the weak carrier. It is spatially disjoint
from the query, and the same exterior witness is used for both
weak-present and weak-absent roles. The query uses a sinusoid with
this estimated phase and the split edge/strong nuisance fit.
A quarter-cycle rotation is the phase control.

Within each aperture, method and blur setting, the decision threshold
targets 5% false admissions on the strong-only role from 16 calibration
sources. Scores are measured on the other 16 sources, balanced by
footprint family. Each source and role has 48 separate simulated
Poisson/read/ADC draws per dose, plus one archived sensor observation.
Intervals resample photos within families. The audit verified all 96
groups of clean CFA means against the capture code and reproduced the
split filter by explicit nuisance fitting on one half and scoring on
the other.

## Stronger blur, σ 0.85

| Exterior-phase query width | Present detected | Strong-only admitted | Exact flat admitted | True gap admitted |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 49.2% | 8.7% | 1.8% | — |
| 64 | 90.2% | 4.4% | 4.8% | — |
| 128 | 99.9% | 5.3% | 2.0% | 2.9% |

The 64-pixel gain over 32 is **41.0 points** with a source-paired 95%
interval of **30.3 to 52.3**. For the eight weakest sources, ranked by
exact-template signal-to-noise on the sharp 128-pixel query, the gain
is **45.1 points** (34.4 to 57.3). The 64-pixel quarter-cycle control
detects 9.4% and falsely admits 10.3% on the strong-only captures.
On the archived draws, the 64-pixel exterior test calls 16 of 16
present and zero of 16 strong-only. The true-gap estimate uses the
eight confirmation sources with exact gaps.

With the exact background and template supplied, detection rises from
68.2% to 94.0% from 32 to 64 pixels. In the separate known-template
128-pixel test with a fitted background, adding the supplied edge
and strong harmonics lowers strong-only false admission from 14.3%
to 7.4%, a paired reduction of 6.9 points (1.8 to 10.7). The 32-pixel
edge fit shows a different tradeoff. It detects more weak strands
than the plane but admits more strong-only controls as well.

The exterior phase error is 0.24 degrees at the median in this
constructed annulus. Performance with unreliable real frequency,
phase and support estimates remains open. These are conditional
detection scores using supplied structure. The
[native model comparisons](local-optical-mixture-1024.md) measure
restoration quality on different tests.

[Source-paired results](results/optical-raw-evidence-v1/publication.json) ·
[All source scores and executable audit](results/optical-raw-evidence-v1/evidence.tar.xz).
