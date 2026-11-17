# Completed full-corpus20k, resumed100k, and calibrated ADC-bin evidence

Recorded: 2026-11-17T09:11:02-08:00 (America/Los_Angeles).

The previous goal turn made progress: full-corpus exposure, execution-quality
checks and queued endpoint reviews. This turn completes the20k training record
and its targeted numerical/actual-image review; the general weak-detail goal
remains active.

The [completed20k report](../docs/full-corpus-control20k-review.md) binds EMA
`633053370bdfb455d738ce0e3af686cb61e8dcac7c501954eb3b2293738a3795` to V120,
all20k steps/320k target slots/80 conditioning chunks and all90,778 training
photo IDs. First full epoch17039;112424 photo visits,106823 ordinary/5601
reviewed. All1000 replayed rows/four chunks equal the abandoned segment.
Source/cache crop boxes106855 are pre-geometry and correlated; native/paired
actual distinct IDs are unrecorded. No lifetime-novelty or pixel-coverage claim.

Retained-loop windows total12490.150s, excluding initialization/final checks;
attempted controller phase wall20104.376s includes stalls/replay/concurrency.
The successful final7k worker took4388.382s. Twenty-one thousand updates were
attempted; the retained trajectory contains20k. Original failure receipts,
partial writes and executed sources remain preserved.

New matched CPU native inference:110 inputs/220 roots/110 actual frozen DINO
executions and110 checked replays,626.509s excluding load. EMA/raw state/RNG
unchanged; all110 V120 outputs bit-exact to previous controls. Independent
FFT/color/pixel audit passes192 metric rows/120 original strata/26 boards and
22 exact-subset triplets. All26 boards were actually viewed. Both
[main GFX](../docs/gfx-qualitative.md) and [cab mesh](../docs/gfx-green-mesh.md)
reviews still lack convincing new faithful crossings. No exact-GT label is used
for ISO100/AHD/JPEG or PIXLS binned references.

Faint mean recovers0.593704 dB from10k, still−0.020610 versus V120. Ordinary
and shadows gain0.008524/0.010466 dB. Fine-band gain moves toward one but spatial
error rises for3/4 materials; selected flat centered RMS also worsens. The
broader full427/known/unseen primary job and subsequent96075-block analysis are
not complete. No chart/registry point is added; V120/V131 remain the last
complete three-panel measurements. README/current recommendation stay V120.

An original reporter import failure and first copied-path recovery admission
failure are retained. Recovery v2 uses byte-identical sealed helper sources,
without mutating the live plan or collected predictions. Its report/artifacts
pass independent audit; the detached launch has no observed OS return code.
The queue constructor now includes helper scripts for future snapshots. Original
training-audit v1 failed on a trailing Python repr; v2 parses actual JSON lines.

The [ADC-bin diagnostic](../docs/adc-bin-consistency.md) respects known
zero-noise quantization intervals instead of point-fitting every decoded
sample. It improves selected mean/band/flat errors, with material RGB regressions;
no noisy/GFX detail claim or default change. Seventeen exhaustive/realizable
checks pass. An initial GPU codec-rounding failure is preserved. Corrected CPU
codec tables match all65536 CPU/CUDA codes under both source precisions; four
actual saved-output comparisons are bit-exact,0 module forwards,2GiB CUDA cap.
This physical GPU work is separate from neural evaluation/training and has no
isolated speed claim. Independent NumPy encoding/FFT/pixel checks pass all48
new outputs,128 faint/64 flat rows,12 additional actually viewed boards and4
exact-subset triplets. Twelve actual GFX/model positive-prior cases bypass by
object identity. Full588-case color collection is running from a frozen plan;
no complete result or automated analysis/promotion is claimed.

The original100k trajectory actually resumes1k Adam/EMA/RNG state with the
100k horizon and next source indices; it is observed past8500. At the later
identity/progress check, control primary104/3162, scene primary456/3162 and full
ADC palette96/588 are advancing. No training is restarted. Full source-bound
[publication](../docs/results/full-corpus-control20k-review-v1/publication.json)
preserves602 files/64 native PNGs; the
[verification addendum](../docs/results/full-corpus-control20k-review-v1/verification-addendum.json)
retains the publisher's empty log-at-archive snapshot separately from its later
completion line. Original receipts/archive bytes remain unchanged.

Current guidance, experiment/research/index pages, full-corpus status and both
GFX maps now link completed20k evidence. Broader scores and the100k horizon
remain pending; the general fine-detail objective is not complete.
