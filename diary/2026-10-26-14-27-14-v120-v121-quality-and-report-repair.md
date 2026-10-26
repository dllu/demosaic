# Publish V120 and V121 quality evidence and repair saved comparisons

Recorded: 2026-10-26T14:27:14-07:00 (America/Los_Angeles).

V120/V121 both finished their original20,000 updates. Their original endpoint
evaluation and independent numerical archive audit also completed. V122 resumed
its exact original worker after the GPU-yield coordinator observed the original
training controller exit. Its log remained unchanged during30,553.50s of yield
(about8.49h); no checkpoint/model/optimizer restart occurred. Preserved the final
coordinator status as a byte-identical public receipt and published V121's
original training accounting.

V120's primary means are37.04008290 photo sRGB,54.31271791 known measured CFA
and54.00872220 unseen measured CFA dB. ADC maximum mean-RGB error is55.52459DN16.
V121 reaches37.04157241/54.32183576/53.98946550dB with ADC maximum1645.36449DN16.
V120 is a useful balanced Small continuation: versus V119 it keeps the photo
score (+.00177dB) while recovering+.21209dB known-camera mean and removing the
2526.70DN16 tested ADC outlier. Versus V115 it gains+.06308dB photo (418/427 source
means rise), with−.01133/+ .00455dB known/unseen changes. This is a documented
gain without a study-specific promotion gate or a broad real-photo claim.

V121's combined cleanup/fourteen-region intervention adds+.00149dB photo over
V120, with paired-source95% interval[−.00080,+.00401] and187/427 source means
rising. Lowest-contrast/high-noise source-balanced projected detail gain changes
.36476329→.36575384, compared with V115 .36421786,V119 .36523151 and V117 .36628753.
This remains substantial weak-detail attenuation, not evidence that the new
material bank solves it. V121's lower unseen mean and large ADC tail remain
documented weaknesses. The next20-region/90784 data preparation is untrained.

The first saved-report attempt stopped because older audits declared two
different material IDs from the new audit. Fixed `matched_material_stage` uses
the candidate audit's declared pair, reuses existing PNGs and renders only the
missing old-control crop from its bound FP32 prediction/exact supervision.
Complete numerical input/target joins, exact archive context/model identity,
file/value hashes and noisy/GT/display equality remain required. The original
failed source/output stays preserved. No model, target or observation is rerun.

The next stage correctly rejected a real GFX conditioning difference. Older
outputs use Haar-shot .0014635775921166604/read1.0715704128646712e−6; new outputs
fall back to nominal-shot .00128/read6.553600000000001e−6 after input estimation
reports insufficient intensity span. The actual old/new RAW/reference arrays,
six regions, WB/matrix and display agree. Default matching remains strict.
An explicit plan option now renders these saved pipelines with profile labels,
`conditioning-different` filenames and an unambiguous no-model-only-ranking
limitation. All other array/geometry/display checks remain. Matching fixed-profile
full-frame comparison against older models is still required; preserve both
the nominal observations and original failures.

Actual positive proofs reproduce both failures with original saved inputs and
exercise the corrected paths without Torch/neural/noise/RAW work. Only exact
owned idle frequency report/mesh controllers were retired with SIGINT after
checking process creation identity, empty outputs and no children. Their
plans/source/claims/logs/terminal states remain intact. The final report queues
are V120/V121 matched-review-v5 and V122/V123 matched-review-v4; their mesh queues
are green-mesh-review-v4 and green-mesh-review-v3 respectively. Training, endpoint
evaluation and independent audits were not restarted or signaled.

The V120/V121 saved comparisons finished all four declared contrasts, each with
14,190 matched primary/analytic observations and full427-photo local detail:
5,124 source/noise/CFA cases and96,075 unique GT blocks. RGB16 verification checks
all four full101.996MP TIFF hashes/types/shapes and921,600 native linear-camera
values against exact FP32 clip/round quantization. Native sRGB quantization is
not independently recomputed.

Actually viewed all four two-source material boards and eight six-region GFX
boards at native resolution, plus the four exact-GT triplets and both V121
two-profile fine-mesh boards. V120/V121 matched nominal outputs retain coherent
larger fence/building edges and quiet sky; foliage stays painterly and neon detail
smears. No clear large V121 detail gain appears. The fine mesh also shows no clear
V121 recovery gain over V120 under either profile: nearby conditioning exposes
more diagonals, while lattice stays weak/soft/irregular and the blue point persists.
V121 used exactly two new root/encoder forwards; both V120 predictions and five
old controls were reused. No RAW/noise/optimizer work was added.

I initially misnamed the second material sources in the repair narrative.
The authoritative metadata and images identify older `212ae12913ef` as forest
canopy and newer `2b5a51667b99` as raccoon fur. Actual IDs, array/target matching
and pixel checks were correct throughout. Kept the original machine narratives
unchanged and explicitly corrected the labels in current docs/new receipts.

Published two native noisy/restored/exact-synthetic-GT triplets per endpoint;
all921,600 panel channels exactly match their audited hashes. Selected material,
GFX and mesh PNGs are byte-identical to actually viewed originals. Independent
NumPy64 checks921,600 V121 mesh-board channels:921,598 exact and two differing by
one DN8 from FP32 rendering. ISO100 real references remain independently captured
and never exact GT. Updated README, current choices, training/source/GFX guides
and54-endpoint PSNR plot/CSV/JSON/SVG/PDF. All52 prior checkpoint identities and
primary means remain exactly unchanged. No graph generation adds inference.

Verified immutable user-facing aliases for both final checkpoints at
`/mnt/external/demosaic/models/v120-final20000.pt` and `v121-final20000.pt`, without
model deserialization/inference. Active parent snapshots remain pinned.
Seventy-nine comparison/material/queue tests and eight history tests pass; Ruff
checks/format and `git diff --check` pass.

Remaining work includes matched fixed-profile full-frame comparison against older
models, detailed ADC-outlier visual diagnosis and completing V122/V123's original
training/review. Broader SOTA/real-photo superiority and100MP-within10s remain
unproven. Keep the full goal active; the next quality experiment should preserve
all existing predictions and treat a changed variance/profile as a distinct,
explicitly bounded operator rather than rerun inference for bookkeeping.

[Primary results and native triplets](../docs/v120-v121-primary.md) ·
[Completed saved/local/native review](../docs/results/v120-v121-native-review-v1.json) ·
[Material/conditioning repair](../docs/results/endpoint-material-and-conditioning-repair-v1.json) ·
[Initial publication checks](../docs/results/v120-v121-publication-v1.json).
The final checks resolve543 local Markdown targets and147 artifact bindings,
preserving all52 prior primary-history identities/means while adding two complete
endpoints. V122 remains the same live worker at logged step17,250; V123 follows.

After checking that none of the five live plans references the mutable selector,
advanced the current general recommendation to V120. All five complete guards
pass before and after; their immutable V115 parents, recipes and inputs remain
unchanged. Current-model/README now reflect the new measured balance instead
of retaining the older recommendation as a documentation gate. V114's lower
tested ADC maximum, V115's slightly higher known mean and V117's slightly higher
photo score remain available and explicit. V120's remaining mesh/profile/SOTA
limits are unchanged by this recommendation.

Preserved the old selector bytes publicly and archived the initial54-point
V114-reference PNG/SVG/PDF before updating the current chart to V120 reference.
Earlier machine receipts/registry remain byte-identical; the selection receipt
maps their old mutable-path hashes to exact archived snapshots. The final
registry is `version-PSNR-history-v121-current-v1.json` and still preserves all52
prior checkpoint identities and primary means. V114's optional eight-view pilot
is retained under a version-specific entry, without implying a V120 pilot result.
[Current selection and preserved provenance](../docs/results/current-model-v120-selection-v1.json) ·
[Current publication checks](../docs/results/v120-v121-publication-v2.json).
