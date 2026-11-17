# Joint colour support for fine carriers

Recorded: 2026-11-16T21:59:16-08:00 (America/Los_Angeles).

Previous turn was substantive progress: sinusoidal fine carrier control,
46 viewed figures,210 passing tests and pushed caa47b77. Current
turn first revalidated exact full producer/predictor/reviewer/publication
owners, no partial full-quality analysis or restart.

RAW-only diagnostic uses both cab profiles/all four512 tiles/both nuisance
arms/left-right ROIs,144 colour rows. Loads RAW/genuine A-only fields only,
no parent/GT/reference. Full local/global linear query map reproduces actual
fits within1.06794e-17; fixed-design variance propagation is not calibrated
SNR/confidence because frequency/weights are selected from A. Dominant nominal
right first-family analytic supports R.14047/G.85567/B.03634 despite RAW-fit
amplitudes approximately33/70/32 DN16. Second family red/blue support nearly
zero. This identifies a possible hue shift from unequal channel shrinkage.

Implemented joint fine support only for the sinusoidal fine branch: sum actual
CFA held-out standardized full/null gains and energies before normalization,
one scalar per direction/pixel/fold. Independent RGB amplitudes/phases and
identical RAW/parent maps retained. Bad R/B evidence can reject a positive
green direction; this is not copied green evidence or forced neutral RGB.
Can admit noisy weak-colour coefficients; not calibrated risk. Broad support/
H1 unchanged. New API fine_support="joint", default independent retained.

217 regression tests pass in37.13s; direct pooled RSS on allCFAs, nonvalidation
NaNs, relabel invariance, adverse red/zero-energy cases, actual delivery and
unchanged broad/H1 controls. Ruff passes. Launched48-case comparison once:
producer981379/create1794895155.15, predictor981584/create1794895162.88,
reviewer981380/create1794895155.17, CPU16/17/two threads. Plan
29d510e2258cb88c34c46811b662c4cb2039f50ba9c6f8f820e23bc018f9d5cd;
modela13cfe5710640014e07f2997955c3fe02fa7ad42f8e56f85cb3b7b92094fd903.
All88 fields reused, zero new NN/DINO/RAW/noise/optimizer calls in this pilot.
All48 corrections closed before quality scoring. Primary analytic localt2
versus independent-colour sinusoidal fine control; NN/six methods/0,2,4 retained.

Caught a shared contact-sheet log filename collision before evidence stages.
Stopped only waiting publication driver981737/create1794895226.07 before it
executed any stage. Preserved queue/source/log/launch and withdrawal receipt;
versioned queue/unique identical contact helper launched driver981819/
create1794895282.28. No inference worker stopped/restarted or source changed.
All seven producer stages/followup/seven corrected evidence stages completed.
Correction561.922s versus566.967s independent support; no100MP timing claim.

Actual native viewing: all46 figures on14 exact sheets. Both cab directions
remain visible with substantially reduced purple/green periodic tint in both
profiles/ROIs, with remaining softness/regularity/incomplete wires. This is
a useful real colour operating point, not exact reference recovery. Sky
unchanged, foliage/bark/fur soft, building bands persist. NN building maximum
65.109→59.704 DN16; analytic154.781→153.657. Cab correction magnitude rises
22.921→27.736 nominal/17.415→20.376 nearby profile; these are changes from
V120, not real-reference errors. Both independent ISO100/AHD references/JPEGs
stay qualitative, never GT/scored, protected/cached/read-only/outside training.

Synthetic cost: analytic1600/far weak1.49991%→0.98935%, increment15.618608→
15.621053 DN16, same quiet5.551996, returning to broad-only. NN weak1.24737%→
0.98711%, increment16.034092→16.035306.400/6400 localt2 controls retained.
No new selected threshold or hidden response loss. All288 original H1 outputs
exact; all48 input/parent fingerprints,50 tiles/100 broad diagnostics and100
fine geometry/full-null diagnostics match independent support. Audit3819
fields/228 finite/114 material rows/14,131,200 channels, max2.8866e-15.

Second RAW-only diagnostic keeps all144 phasors/phases/noise maps exact,
changes only support; dominant nominal NN right means now .90135/.67249
common acrossRGB. Tool session68363 reported143 after complete atomic JSON
and final log rows existed; cause unknown, source/log/result/terminal receipt
preserved without retry. No inference worker was affected.

210 exact final archives/168 executed sources bind46 actually viewed figures.
Original preparation/receipts remain intact. [Completed report](../docs/joint-fine-colour-support.md)
and [exact publication](../docs/results/neural-nuisance-joint-fine129-v1/publication.json).

Separate fresh coloured benchmark now has48 new V120 full parents/96 genuine
masked fields,144 explicitly counted root/encoder calls, all91/backbone tensors
unchanged. Four fixed reconstruction variants are running; no new-cohort
quality peek. [Benchmark](../docs/coloured-fine-wire-benchmark.md). Original full
guided1164-case producer/auditor/publication have meanwhile completed normally;
70 native figures await actual review, no full quality conclusion claimed yet.

Final independent verification passes:210 exact archives/46 PNGs/168 current-
and-frozen Python sources,31,703,424 exact native contact RGB channels,912
summary fields and643 local MD links.103 coloured-benchmark admission archives/
164 source members and six full-study queue archives also exact. First
verifier assumed a group field absent from single-manifest viewing receipts;
preserved source/log, then accepted that schema only for sole base manifest,
without changing receipts or numerical outputs. Eight400/6400 analytic/NN
mean rows are all-field exact. [Verification](../docs/results/joint-fine129-publication-verification-v1.json)
and [exact source/log](../docs/results/joint-fine129-publication-verification-artifacts-v1.json).
