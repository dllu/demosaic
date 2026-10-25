# V116 full quality and broad local-detail review

Recorded: 2026-10-24T22:32:38-07:00 (America/Los_Angeles).

V116's original training, eight evaluation stages, independent numerical audit,
direct V114 comparison and additive full-photo local-detail audit have all
completed; their original owners exited. No successful neural work was repeated
for review/publication. The original evaluator made4586 model/encoder calls and
retained14,190 numerical observations, plus standing GFX contexts and the full
102MP output. The independent NumPy64 audit checks every numerical observation;
the direct comparison pairs them with retained V114 inputs/targets/transforms.

Independent photo/known-CFA/unseen-CFA means are36.97477819/54.28701282/
53.99496730dB. Relative to V114, changes are−.00495243/+.00073837/−.00793447dB;
149/427 photo-source and2/4 known /1/5 unseen scene means improve. The eight-pixel
weak carrier rises from.13371 to.19123 at level.18, contrast.02, ISO12800, while
noncarrier RMS rises. Four-pixel response remains nearly absent, sixteen-pixel
gain falls, and ADC worst bias grows from51.731 to239.154DN16. The new worst
case954 is magenta hue300°, saturation.50, peak.90, GRBG. This is a useful
analytic tradeoff, not a general quality improvement.

The full-photo local audit uses427 photos,5124 source/noise/CFA observations,
96,075 unique GT blocks and1,152,900 block observations per method. Its weakest
stratum includes326 photos/15,008 unique blocks. Source-balanced high-noise gain
is.36334483 for V114 and.36301904 for V116; band-error RMS is effectively
unchanged. Explicit cosine/even-FFT coefficients agree within1.83e−14 across
2,401,875 transforms. It completes in40.79s with no Torch, noise generation or
RAW decoding. The earlier four-source/eight-view pilot keeps its own targets,
policy and weighting; its values are not substituted into the broader result.

Actually viewed nine original PNGs containing50 native160px display cells:
two bark/canopy V116 triplets, the matched material board, both three-region GFX
boards, and matching V114/V116 paraglider and building/cloud triplets. Both
models lose fine bark/leaves, suspension lines and cloud detail; foliage stays
waxy and saturated neon smeared. Fence/building geometry is coherent and sky
smooth. No clear visual recovery appears in these examples. GFX ISO100 remains
an approximate independent reference, not GT. For the generic pairs,307,200
noisy/GT RGB8 values match exactly, along with actual retained WB/matrix/targets.
A first metadata check stopped because generic crop metadata omits WB; a fresh
check obtains it from the retained supervision arrays. No model was run again.

Both V116 TIFF hashes/types/shapes pass:8746×11662×3 uint16. All460,800 linear
RGB16 values in six retained native regions exactly match FP32 clip/round
quantization. The recorded113.86s FP32 interval is a separate observation, not
a controlled speed improvement. The100MP/10s goal and broad real-photo/fine-detail
quality requirements remain unmet.

[Full report](../docs/v116-quality.md), [GFX gallery](../docs/gfx-qualitative.md),
[complete evidence](../docs/results/v116-quality-complete-v1.json) and
[local-detail data](../docs/results/v114-v116-local-detail-v1.json) are published.
Current guides now show completed review and measured tradeoffs. V114 remains
the general baseline for its better photo/color balance; the reviewed masks
remain useful data corrections, but their isolated effect was not measured.
All original plans, executed sources, failures and receipt bytes stay preserved.

PSNR history now contains49 completed primary endpoints through V116. All48
previous points remain exactly equal; old figures/registry/selector are backed
up under the publication workspace. PNG/SVG/PDF and the versioned CSV/JSON were
rebuilt from original source-bound reports, with no inference. The chart was
actually viewed. All eight history tests pass; the first test command omitted
the scripts import path and stopped during collection, then the corrected
repository path succeeds. Ruff/format and whitespace checks pass.

The first publication verifier assumed every downstream status used the
`queue_plan` key; existing audit/comparison controllers use `plan`. A fresh
verifier reads each recorded schema and retains exact plan hash checks. The
failed source/log remain preserved; original jobs, sources and metrics are unchanged.

[Publication checks](../docs/results/v116-quality-publication-verification-v1.json).

