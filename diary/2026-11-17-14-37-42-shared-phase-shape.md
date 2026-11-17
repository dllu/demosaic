# Measure shared RAW waveform fidelity

Recorded: 2026-11-17T14:37:42-08:00 (America/Los_Angeles).

Reused the nominal eight-pixel guarded predictions as exact controls.
The shared shape uses a noise-precision-weighted rank-one knot profile
per direction and discovery fold, with separate signed amplitudes for
the Bayer colors. All frequency and edge decisions match the independent
fit. The own-color held-out comparisons, original seven-degree
reliability penalty and delivery weighting remain fixed.

ISO400 far chroma increment error improves from 3.68524 to 3.63150 DN16
at the 0.02 DN16 development setting. At matched quiet RMS, the far
response is close at 22.13% independent and 22.10% shared. ISO400 near
weak response at equal quiet is 12.00% independent and 7.65% shared.
All eight near ISO400 sources increase increment error at both frozen
settings. ISO6400 near adds less correction on the no-wire role and
recovers less true weak signal. The common waveform stays opt-in.

Both GFX families and four synthetic boards were viewed at native crop
resolution. The sky matches V120 exactly, and the cab lattice remains
incomplete. The first collector compared a serialized list directly
with a runtime tuple. The corrected collector compares the numeric
arrays and completes all 104 fits. The independent audit rechecks 2,816
metrics and 120 retained camera panels. 149 focused tests pass.

The larger-corpus trainer reached update 35,900 and the 50k review
watcher remains live.
[Shared shape report](../docs/shared-phase-shape.md) ·
[Training coverage](../docs/full-corpus-scaling.md).
