# Test bright cross-edge validation on fresh RAW observations

Recorded: 2026-11-17T15:24:49-08:00 (America/Los_Angeles).

Froze bright cross-edge weights 0.5 and 1.0 alongside independent
and same-side validation. Dark-side evidence remains confined to
the fitted side. Fractional weights multiply the score numerator
linearly and enter the variance squared. Rebuilt the V143 parent
from 60 fresh observations, with eight near geometries at both
priors and two far controls at each.

At matched ISO400 near quiet RMS, same-side response is 3.94%
versus 3.46% for the original, 3.56% for half cross-edge and 3.36%
for full cross-edge. ISO6400 responses remain around 1.4%. The
bright-side behavior differs from the previous cohort. Both
camera sky views match V120 and the real fine cab lattice stays
incomplete.

The ISO400 measured weak donor guides average 0.047 native bins
of error. The guarded search increases error to 0.464 bin. A
post hoc fixed-guide replay on all eight lower-noise near sources
raises response from 3.94% to 6.12% at matched quiet error and
reduces increment RMS from 15.15961 to 15.14448 DN16. It keeps the
same-side validation and measures a synthetic-only intervention.

Viewed all 14 native boards including the two fixed-guide crops.
The main independent audit checks 2,144 reductions and the diagnostic
audit checks 48. 146 focused tests pass. The first summary attempt
stopped on a missing frozen import. Supplying the prior frozen
dependency completed the summary from the same saved predictions.
[Results and native comparisons](../docs/asymmetric-phase-evidence.md).
