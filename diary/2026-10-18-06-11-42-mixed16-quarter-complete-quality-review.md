# Complete matched160k-example quality review

The frozen quality controller2667688/1792305841.61 and its final child exited
successfully after all primary, analytic, real-camera, color, highlight,
artifact, source-sensitivity and own-parent progression stages. Its terminal
status is `completed-mixed16-quarter-panels-statistics-artifacts-hue-sensitivities-and-parent-progress-awaiting-native-quality-review`.
All50 inputs/190 frozen-file guards remain unchanged. No inference was restarted.

Finished actual original-resolution hue and highlight board views. Combined
with earlier recorded inspections, all146 report-native triplets/202 cells
are now viewed. The publication checker independently compares every cell
with its final original PNG and requires exact complete crop metadata. Early
photo-sidecar and additional-color aliases match final records and PNG hashes
exactly. Seventeen published PNGs are byte copies, including two exact-GT
photo triplets per new model and standing GFX foliage/fence triplets. Real
ISO100/AHD/RawNIND references remain explicitly not exact GT.

The [report](../docs/packed-isotropic-mixed16-quarter-review.md) and
[result registry](../docs/results/packed-isotropic-mixed16-quarter-review-v1.json)
record the complete decision without promotion. Registry SHA256 is
`1ff35a04b37ea7f11fcd739e23dfbd9ed530f9cd4717607a8605f15ee36298d7`.
The private publisher and independent report checker are retained in
`/mnt/external/demosaic/benchmarks/mixed16-quarter-native-review-v1/`.
The checker verifies24 top-level references,17 PNG copies,146 checkpoint hashes,
44 primary table scalars,6 timing values,12 color values,9 cohort values and
21 local report links. The [publication-check receipt](../docs/results/mixed16-quarter-public-report-check-v1.json)
is an exact copy of its private result. An additional read-only check confirms
the own-parent photo gains/intervals and50/190 frozen input/guard counts.
No model inference was run by these publication checks.

Photo sRGB PSNR is28.70933/29.05806dB for new V72/V73, versus
29.73199/29.95315 for older equal160k-example RAW controls and34.89933/35.93298
for mature V43/V63. Own2k progress is+.53338/+.87718dB; DINO−noDINO is
+.34873dB, paired source interval[+.33648,+.36059]. Known-camera scores improve
over older equal-example controls while unseen scores decline. These conditional
results from one training seed cannot isolate the batch effect or certify a
general foundation benefit. Selected real crops remain grainy with weak fine
foliage/fence structure. The uniform-color noise/bias tradeoff persists.

Full101.996MP FP32 restores take154.88/168.78s for the new pair. Neither quality
nor speed meets the project target; V43 remains the README working reference.
No training extension is launched. Preserve both full10k states and original
40k/640k-example schedules; analyze the now-completed queued CUDA inference
profiles and EMA comparisons before selecting the next bounded trial. Isolated
EMA results still require a whole-step experiment before production adoption.
The unchanged FP16 precision gate, training exclusions and closed protected-final
scenes remain in force. The project goal remains active.
