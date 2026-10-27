# Measure heldout faint photographic ADC detail

Recorded: 2026-10-27T02:52:03-07:00 (America/Los_Angeles).

Prepared a distinct16-observation faint-ADC panel: four established photographic
contexts (bark/fur/two public-native estimates), all four CFAs. Preserve each
camera channel's whole256 DC and scale deviations by.025; fixed FP64-code16-bit
ADC/black.03, no stochastic draw/spatial interpolation/RAW decode. The earlier
attempt to reconstruct old ADC packed bytes from archived reference-white targets
failed exact hashes; no old prediction was adopted and no old inference replayed.
New observations require16 V120 baseline calls,16 V129 calls and16 V130 calls,
48 total. This supplements, and does not reset, the existing86-call quality scope.

Independent long-double rational input audit passes786432 target values and
1048576 ADC samples. Actual training-disjointness checks pass90782 Commons train
rows,128 native records and64 paired cases; val rows/protected-ID policy metadata
are not training records. Both completed methods preserve weights/backbone/RNG;
V129's full-model hash matches its original86-call collection.32 calls complete,
V130's16 remain pending behind the original1000-update producer. No old control
or prefix was repeated. Both control collectors wait for48GiB admission, with
8GiB CUDA cap/32GiB runtime floor and1200s worker bounds; the queued V130 endpoint
retains its original producer deadline. No automatic retry/reset.

A reporting-schema omission kept source case/GT-label metadata at case level.
Report-only derivation attaches that immutable provenance to observations without
changing inference plans, arrays or predictions. Public preparation includes the
per-observation fields for future panels. No collection was rerun for metadata.
Independent FFT/display audit passes32 rows/eight summaries/200 scalar fields,
2150400 primary PNG channel values. The separate fixed40x camera-DC contrast
view is display-only, applied identically after inference; all1228800 actual
saved enhanced-panel channels match independent long-double rendering exactly.
All four normal triplets and four enhanced comparison boards were actually viewed
in two native sheets, without resizing. Published8 unchanged images contain
2746368 total RGB channels, with source/ROI/weights/ADC/display metadata. Two
Commons targets are exact synthetic processed targets; public-native estimates
remain approximate, not GT. The original GFX pairs remain separate.

V120 has.956–.998 projected band response on the transformed targets; this
argues against a universal faint-detail precision ceiling, not against noise-
conditioned detail losses. Strong structures now fall in the same low-contrast
bin, so reused original-target reference masks provide descriptive stratification.
Independent FFT/dot-norm reductions verify360 scalar fields across120 rows/30
source-bin/method summaries, max5.92e-14 discrepancy. No output-based selection.
This stratification follows V120/V129 outputs and precedes V130 outputs.

V129 original0–2% fur gain.85184→.87003 but relative error.28624→.28712;
2–5% fur gain.83387→.85593 and error.31109→.29770. Grass gain.96548→.94039,
error.24896→.24865; wood essentially unchanged with slightly higher error.
Ordinary faint-target mean sRGB67.480668→67.417249dB, camera75.482160→75.385897.
These deliberately flat synthetic-target scores are not full427-photo scores.
Visible changes are small. The report records positive fur changes and weaknesses
together; no FP32-trained quality conclusion while V130 is incomplete.

Eight operator/subprocess tests pass: phase/code geometry, DC/detail scaling,
exactly-once collectors, saved-control wiring, preserved failure and rejection
of changed producer identity. README/current quality docs link the new comparison.

Final publication verification passes8 unchanged PNGs/2746368 RGB values,245 local links,14 frozen plans and57 unchanged inference source files. All13 current quality/dependent/precision owners are verified live, with at least1586 new frequency photo records already written.37 focused tests and Ruff pass; verification adds zero neural/noise/RAW work.
