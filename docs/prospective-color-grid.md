# A prospective hue grid for the palette review

A larger uniform-field diagnostic is frozen before inspecting the palette
trial's separate evaluation outputs: **147 colors and grays, 1,176 saved native
256px observations**. It supplements the four colors chosen after the original
fabric failure. The preparation receipt records the state before inference.
[Complete definition, observation hashes, input audit and queue launch](results/prospective-color-grid-preparation.json).

The parent model's failures motivated this grid, so it is not a blind benchmark.
Both preparation snapshots show the wider arm still training, with none of the
separate trial-score reports present. Existing training monitors are separate.
The grid is excluded from training and does not alter either arm's data or
4,000-update schedule.

## Fixed coverage and limits

| Dimension | Values |
| --- | --- |
| Hue | 24 angles: 0–345°, spaced 15° |
| Saturation | .50 and .98 |
| Scene-linear RGB peak | .02, .18 and .90 |
| Neutral fields | One gray at each peak |
| Bayer patterns | RGGB, BGGR, GRBG, GBRG |
| Noise | ADC-only and ISO12800 protocol prior |
| Camera/WB | Original evaluation matrix and WB[2,1,1.5] |
| Native input / report ROI | 256×256 / [48,48,160,160] |

Hue/saturation are applied directly to **linear RGB**, rather than encoded sRGB
or a perceptually uniform space. The high-noise condition uses shot=.00256 and
read variance=.0000262144; these are declared priors, not a camera ISO calibration.
Both conditions retain 16-bit ADC quantization and black=.03. There is one fixed
noise observation per color/condition/CFA, with seed 20261017 and source-keyed
noise independent of model ordering.

Every clean RGB/camera target is constant and strictly inside white. The noisy
ADC still clips: the saved set has 7,241 saturated samples and 1,880,430 negative
black-subtracted samples. The plan's short “no clipping” description refers to
clean targets, not noisy observations. The same physical ADC behavior is used
in the photographic evaluator.

The .50-saturation fields stay within a channel ratio of 2; .98 reaches 50. This
spans moderate and strong chroma beyond the original smooth tint bound of 5,
without restricting the check to the earlier warm/cyclic colors. It is still
one camera/WB, three peaks and a finite analytic grid. It cannot establish
natural-photo quality, training-repeat uncertainty, a training cause or SOTA.

## Complete input verification

The [CPU preparer](../scripts/prepare_color_grid.py) freezes 187,219,159 bytes
of compressed observations. The separate
[input auditor](../scripts/audit_color_grid_inputs.py) verifies every file's SHA,
shape, dtype, finite values, Bayer phases, WB/matrix and spatially constant GT.
NumPy64 inverse-camera reconstruction differs from the stored F32 target by at
most 6.60e-8. Independent variance reconstruction differs by at most 2.22e-10.
All 588 ADC-only inputs match independent F32 quantization bit for bit; all 12
high-noise preview/CFA cases reproduce from their declared seeds exactly.
No CUDA context, source photograph or cold RAW decode was needed.

The source plan SHA256 is
`93aad6a67b9f4a9a59d76aae8371018a6aa16a8861c4b28c902f243879fdd18a`.
The actual generator, protocol, source files and independent receipt are retained
beside it. All observation hashes are in the public preparation receipt.

## Queued evaluation and native previews

The [CUDA evaluator](../scripts/evaluate_color_grid_cuda.py) will compare the
same observations for the V58 parent, V59 control, V60 wider palette and optional
genuine released RAW reference. The queued run includes all four. Joint models
use FP16 with physical FP32; the released RAW cascade retains its validated
contiguous layout and IEEE FP32 computation. No correction or target fitting
is added.

The five-script toolset and model package are frozen separately. Controller
1689505 (creation 1792197467.81) was checked waiting for palette owner 1648057's
actual successful exit, with no GPU child. It confirmed that exit on October 17
at 00:50 UTC and started the frozen grid. It retains
all 4,704 full F32 predictions and runs an independent CPU audit of 28,224 metric
fields and all native panel pixels. Twelve native triplets still require
actual visual inspection after inference. A first waiting controller was
superseded before any GPU work to correct an unintended layout conversion;
observations and preview cases never changed.

The evaluator reads and verifies the observations once, caches them on CPU,
and reuses them across methods. Only noisy inputs/conditioning move to CUDA;
clean targets stay on CPU. The main training/evaluation workflow remains the
sole GPU owner until it exits. Observation timeouts do not trigger a restart.

Three native previews are selected in the frozen plan, shared across methods:

| Field | Peak / saturation | Condition / CFA |
| --- | --- | --- |
| Warm hue30° | .90 / .98 | ISO12800 prior / RGGB |
| Magenta hue315° | .90 / .98 | ISO12800 prior / RGGB |
| Neutral gray | .18 / 0 | ISO12800 prior / RGGB |

Each panel will be 160×160 at one image pixel per PNG pixel, with common matrix,
WB, display exposure×1 and ROI. No resizing or sharpening. The third panel is
exact uniform analytic GT. These previews complement the photo and standing
GFX foliage/fence triplets; they do not replace them.

Grouped mean/median/p95/worst channel bias, total error and spatially centered
error will be descriptive values for this fixed grid, not confidence intervals.
Centered residual includes remaining sensor noise and possible false structure;
its cause requires pixel inspection. The
[saved-array auditor](../scripts/audit_saved_color_flats.py) now supports this
validated grid; its original 32-case/192-field legacy recheck still agrees to
2.23e-16 and both original native triplets rerender exactly.
The separate [group-summary auditor](../scripts/audit_color_grid_summary.py)
checks complete case labels and recomputes all descriptive statistics after
the saved-array audit succeeds.
