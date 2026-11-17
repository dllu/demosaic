# Weighted RAW refit after held-out validation

Recorded: 2026-11-17T13:23:46-08:00 (America/Los_Angeles).

Admission uses the same held-out RAW gate, frequency guides and
discovery shrinkage as the full eight-knot fit. The two refits
estimate the delivered camera-RGB correction from all actual CFA
sites of the corresponding color. The weighted fit uses the
direction's pooled support with a weight floor of 0.25.

All 384 synthetic views and eight GFX cases ran in 329.24 seconds.
The 392 threshold-2 controls and saved fold diagnostics reproduce
exactly. The two independent audits cover 1,728 image reductions
and 192 separate refit reconstructions. All twelve native boards
and both weighted triplets were viewed. The focused suite passed
144 tests.

At the tight calibration budget, ISO400 far weak response rises
17.54% to 21.07%, with lower weak increment RMS and quiet RMS
2.51694 to 2.52216 DN16. A descriptive common scale matches the
measured quiet RMS exactly and retains 19.16% response. All eight
geometries improve both weak response and increment error in this
check. The ISO6400 near result is worse. The V120 sky is exact, and
the weighted left cab view has stronger diagonals with fine crossings
still unresolved. The gains are for the retained lower-noise panel.
[Numerical results and native crops](../docs/phase-refit-delivery.md).

The live 100k trajectory has reached 29,350 updates. Its 50k review
continues to wait for the immutable receipt. The large short-20k
and whole-scene evaluations have 733 and 763 of 3,162 cases, and
the faint ADC collection is at 279 of 428.
[Training progress and milestones](../docs/full-corpus-scaling.md).
