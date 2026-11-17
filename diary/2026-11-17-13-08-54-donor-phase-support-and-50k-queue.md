# Donor waveform harmonics and the 50k native review queue

Recorded: 2026-11-17T13:08:54-08:00 (America/Los_Angeles).

The waveform test uses the corrected frequencies from disjoint donor
RAW. Donor folds compare the full knot representation with a null
that drops one harmonic at a time. Only the admitted harmonic orders
transfer. The query fits its own coefficients and validates them on
its held-out CFA sites.

All 384 synthetic views and eight GFX cases ran in 699.49 seconds on
two CPU threads. All 392 full phase-fit controls match the retained
predictions at threshold 2. The separate audits checked 288 donor
scores, 392 query basis bindings and 1,728 image reductions. All
twelve native boards were viewed. The focused suite passed 143 tests.

At the 0.02 DN16 quiet budget, ISO400 far weak response is 17.536%
full, 16.909% donor-selected and 7.448% fundamental-only. At ISO6400
far, donor selection gives 2.087% vs 2.294% with the full basis, with
increment RMS 22.46015 vs 22.46433 DN16. The full basis recovers more
weak signal in all 12 held-out budget cells. The main sky matches V120
in linear RGB. Real fine cab crossings remain unresolved.
[Harmonic test and native images](../docs/donor-phase-support.md).

The original 100k run logged 28,000 updates. The native 50k review
waits for its immutable checkpoint receipt. The preflight verifies
110 shared observations and 220 saved V120 and long-20k control
predictions. The queued review uses 110 new model calls. The trained
50k state, metrics and actual native viewing remain pending. The
local queue plan is `.cache/experiments/full-corpus-long50k-native-queue-v1/queue-plan.json`
with SHA256 `3ec4b1dfabe0cc274e5d1dd27ac3781abb5ce88ed9df108ddba2a92aaba4bcb8`.
[Training schedule and checkpoint reviews](../docs/full-corpus-scaling.md).
