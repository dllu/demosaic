# Inspect V101 sampling proportions and clean targets

Recorded: 2026-10-22T13:13:44-07:00 (America/Los_Angeles).

The previous turn made concrete progress by refreshing the Q2/Sony/GFX50R
comparison with V84/V100 (c5675ca). Revalidated the live V101 worker and broad
evaluation/full-frame controllers this turn. Their frozen inputs and actual
numerical source remain unchanged; no training was restarted.

Inspected the active frozen clean reader rather than starting another model
while V101 trains. The `.15` weak-texture setting is an absolute Commons-domain
fraction inside the existing `.20` synthetic total, about75% of synthetic
samples. It does not mean15% of that component. The `.05` ROI setting is
conditional on a photographic Commons sample. Clarified those denominators in
quality-first-training and training-pipeline.

Reconstructed the deterministic seed59 full10,000-step/B16 schedule using the
actual frozen `training_domain`/`domain_indices` functions and the reader's
selection. It schedules4,998 Commons,2,532 native and2,470 paired steps.
Of160,000 examples,55,843 are photographic Commons,11,970 weak synthetic,
4,106 other synthetic,8,049 flat fields,40,512 native and39,520 paired.
The photographic row includes2,844 reviewed ROI samples (5.093% of photos,
1.778% of all examples); each reviewed source is scheduled443–517 times.
These counts describe the full schedule, not completed consumption by the
currently running trainer.

Actually reconstructed the earliest scheduled clean sample for each of the
six reviewed sources at indices15/96/179/458/594/739, using the copied active
reader, seed59 and native256. All are finite FP32. An in-process counter would
reject any optical-PSF invocation; none occurred. A contrast wrapper captured
the actual before/after intermediate without changing draws. The lichen draw
at index179 scales deviations from the per-channel mean by .191659; the
remaining five draws have no attenuation. The affine relation holds within
2e-7 in linear units. This separate CPU process has no access to the running
worker's RNG/state and runs no denoiser, optimizer or noise simulation.

Viewed all12 before/after native160 cells at original resolution. Fine wire
grooves, cloth folds, lichen filaments, net lines, painted-board grain and
wool structure remain visible in the generated targets. The lichen becomes
much weaker in contrast with geometry retained. This checks the intended
data transformation, not whether the trained model will recover that detail.

Published a native two-source lichen/net illustration and complete provenance
in `docs/images/training-v101-targets-native.png/.json`; actually viewed all
four displayed cells and verified they are unchanged copies of the review
board. Sources are GT1976 and Basile Morin,CC BY-SA4.0, with links/attribution.
`docs/results/training-v101-sampling-and-targets-v1.json` binds the frozen
recipe/readers, exact counts, six actual read records, float hashes and views.
Private numerical artifacts remain in
`.cache/current-quality-20261022-v1/training-data-v101-v1/`.

Validation passed for18 bound artifact references, all six finite target pairs
and float hashes,12 review/four published native-cell hashes, full schedule
totals and updated local links. The three live training/evaluation/full-frame
plans still pass their guards; all original controllers/workers remain live.
