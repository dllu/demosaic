# Native camera-linear targets

Prepared 53 ISO50/100 training references from 31 scenes into a 118 MB uint16
cache, using the already downloaded public train32 RAWs. Two Nikon D40 sources
are too small after 8× binning and were rejected. Four CFA phases are aligned
before averaging, preventing the centroid mismatch of separate R/G/B boxes.
Tests cover linear color fields and quadratic gray fields for all CFA patterns,
sub-8-bit signal retention, noise reduction, protected splits and checksums.

Connected this source to training with an explicit native fraction alongside
the existing paired and Commons domains. Native camera RGB keeps its original
WB/matrix, with fresh exposure and physical synthetic noise. Targets are
low-noise estimates, not exact RGB GT. Source noise/clipping remain.

Added optional per-step data RNG isolation for matched source substitution and
resume checks for native manifest/fraction/RNG protocol. Native-only and mixed
three-source CPU resumes reproduce weights, EMA and batch hashes exactly.
All 176 tests and Ruff pass. A 16-step CUDA smoke using the real cache and V16
EMA exercised all domains with finite losses and gradients.

V18 joint and V19 refiner-only controlled continuations remain in progress to
5000; no change to their loaded source or schedules. V16 remains the reviewed
model. Native-target pilot comparison is next. The full quality and speed goals
remain open; no performance claim follows from successful data preparation.
