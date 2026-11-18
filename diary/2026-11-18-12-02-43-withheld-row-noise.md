# Tested withheld detail under correlated readout rows

Recorded: 2026-11-18T12:02:43-08:00 (America/Los_Angeles).

A 72-source synthetic Bayer stress test compared pixel holdout with
complete-row holdout under fixed pointwise read variance and different
readout correlation. With 50% row sharing at the nominal threshold,
pixel holdout approved 85/96 smooth nulls. Complete rows rejected all
of them and reduced mean true horizontal response from 68.18% to
37.28%. With all read variance shared by row, the covariance score
suppressed the true waves at that nominal cutoff. The four comparison
boards and four native triplets were inspected. No actual-camera
noise law was changed.

The comparison began while the localized spatial training arm was
still running. A paired follow-up also started on disjoint distant
RAW calibration strips at the same physical rows, including genuine
horizontal stripe contamination.
[Stress test, native crops and archived receipts](../docs/withheld-row-noise.md).
