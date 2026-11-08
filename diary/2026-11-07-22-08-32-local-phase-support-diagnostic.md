# Measure spatially local evidence at fixed green-phase frequencies

Recorded: 2026-11-07T22:08:32-08:00 (America/Los_Angeles).

The previous turn was a verified wait: actual PID/create-time observations
confirmed that V175 had completed six continuation passes and was still
advancing, with its completion watcher and both V178 watchers live. This turn
uses CPU-only cached training data to investigate a spatial-support weakness
of globally transported spectral features, while those jobs keep their fixed
recipes. No new GPU or neural work is started by this diagnostic.

A pure NumPy reference measures an externally selected frequency in clipped
rectangles after removing each rectangle's own unweighted affine plane. Full
conditional variance includes that nuisance fit. Summed-area moments avoid
constructing each patch. Twenty CPU tests match independent direct QR rows,
including heteroscedastic noise, borders, affine invariance, constants and
variance scaling. This is a mathematical/reference primitive, not a learned
RGB component or an FP32/GPU implementation.

The frozen study reuses rank 1 from V177's lower-index-green direction for
each of the 1,228 member observations in 307 noisy mesh batches. The other
phase is measured at those fixed bins. Nominal packed boxes 33/65/129 and
81 fixed centers give 298,404 local windows. Input RAW/variance/CFA values and
all four observations' measurements are committed to a durable journal before
targets/pairs are interpreted. Clean targets then supply score-only coefficients,
pre-ADC conditional variance and exact counterfactual blank support. No bin
is reselected; no target or other-phase measurement changes it.

All-present signal-containing means rise 5.749→12.572→21.761 with box size;
blank means are 0.979/0.977/0.943, with 614/614/582 blank-contributing observations.
All 614 absent means are 0.983/0.980/0.985. The largest box leaves fewer pure
blank footprints. Among the same 158 of 170 strong-global present observations
that retain blank windows at every size, signal-containing means are
18.912/44.466/78.301 versus blank means 0.976/0.978/0.915. This common-case
restriction is a disclosed posthoc sensitivity analysis, and strong-global
conditioning uses the same other-phase data rather than an independent test.

Absent nominal powers≥4 occur in 827/827/826 of 49,734 windows per size, about
1.7%; none reach 16 here. Many supported windows remain weak. These are
correlated training windows and coupled members, not new independent scenes
or calibrated false-discovery probabilities. No hard threshold is adopted.
The useful next hypothesis is continuous local evidence alongside global
frequency context. This does not show V178 hallucinates or prove another
feature path will improve its actual learned restoration.

The actual CPU process PID 561293/create 1794117575.47 finishes successfully,
with 3,684 input and 3,684 score-only clean projections. Its peak RSS is
124.68 MiB, nice 10 on CPUs 6/7, with no Torch/rawpy, model, parent/DINO,
checkpoint, source render, sensor draw or original/RAW-decoder work. Input
fingerprint bindings 921, all 1,228 fixed bins, all 3,684 scored records and
all 298,404 window powers pass. Both journals remain in the local cache.

The first CPU reducer stops on an incorrect bit-equality requirement between
complex abs-squared and separately summed real/imaginary squares. Its source
and failure log are preserved; a new reducer checks the original complex
arithmetic exactly plus an independent rounding-bounded expression. Maximum
relative difference is 8.02e−16. No scientific measurement prefix is rerun.
Independent native QR on first-four batches, every member/scale, corners and
center checks 288 noisy/clean rows. Maximum coefficient/variance differences
are 1.22e−13/1.98e−14 under the fixed 1e−9 tolerances.

All 21 descriptive groups and 15 chart points are retained. The first chart
was actually viewed and showed annotation overlap near the blank curves;
the additive v2 moves labels into clear space without changing points. Both
PNG/SVG/PDF versions and renderer receipts are preserved. The final chart was
actually viewed. This is a scientific feature plot, not resized photographic
crops or a model quality report. No new restored RGB/native triplet is claimed.

The existing 97 neural files, V175's 96 original sources and 18 completion
helpers stay unchanged. No new external artifact is written. Both protected
GFX families, siblings, JPEGs and original/unavailable media remain unused in
this study and excluded from training. Final V175 and V178 quality/native
comparisons remain required for the actual fine-fence/sky objective.

[Support diagnostic and limitations](../docs/local-phase-support.md) ·
[Exact sources, measurements, plot points and verification](../docs/results/v179-local-phase-support-v1.json).
