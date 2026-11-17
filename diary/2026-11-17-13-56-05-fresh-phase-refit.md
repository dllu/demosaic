# Fresh weighted RAW refit comparison

Recorded: 2026-11-17T13:56:05-08:00 (America/Los_Angeles).

The frozen weighted refit comparison runs 96 new observations
from eight procedural geometries and 16 separate donor noise draws.
All 16 donor frequency pairs are within 0.091 native Fourier bin
of the exact geometry. The 32 CPU V143 EMA calls take 1,265.19
seconds, with 1,366.24 seconds for the complete collection.
Both arms use identical saved parent pixels. The matched parent
device check differs by 0.00024 DN16 RMS in one earlier query batch.

ISO400 far weak response rises from 20.94% to 23.66% with slightly
lower measured quiet RMS. Both arms add about 0.039 DN16 over V143
against the 0.02 DN16 development target. The same eight independent
sources improve weak response and increment error after a diagnostic
scale to exactly +0.02 DN16. The calibrated tight ISO6400 comparison
shows no meaningful gain. Background-only fine errors are almost
identical at ISO400 far. The two standing real-camera families
reuse the previous operator's native images.

The first independent image replay rounded the scaling through
float32. The float64 replay validates all 768 reductions and the
16 frozen calibrations. Both audit attempts and four viewed native
boards are preserved.
[Fresh image and numerical comparison](../docs/fresh-phase-refit.md).

The long 100k trajectory logs 32,200 updates. Its verified
30k prefix covers 480,000 slots and 160,479 ordinary photo visits.
The 50k native review awaits its immutable checkpoint. The full
short-20k and whole-scene panels are at 820 and 805 of 3,162
cases. Faint-ADC collection is at 318 of 428.
[Training coverage and milestone status](../docs/full-corpus-scaling.md).
