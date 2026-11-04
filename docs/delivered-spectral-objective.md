# V153: spectral supervision on the delivered output

This active matched trial tests a concrete mismatch exposed by the
[completed V152 crossover](support-crossover.md). Most of the relative head's
additional quiet-region error follows its frequency proposal under fixed maps.
Opening support raises synthetic mesh response but increases actual blank/quiet
error, without convincing new real fence crossings. Changing only the support
map does not fix the proposal's quiet cost or natural-band attenuation.

The existing spectral term supervises a proposal **before** overlap synthesis,
spatial support and signed demosaicing. Its target coefficient therefore does
not directly describe the RGB correction that reaches the output. Pixel and
gradient losses already see delivered RGB. V153 changes only the spectral term,
with the same relative-phase architecture and all training inputs held fixed.
**Restoration quality is not measured yet.**

## Three fixed objectives

All arms use `LateSpectralRelativeDetail`: 33,713 parameters in 13 tensors,
initialized identically. All 86 neural source files remain byte-identical.
The [recipe](../configs/quality-v143-delivered-objective-v153.yaml) fixes:

| Arm | Spectral error | Channels |
| --- | --- | ---: |
| Pre-control | Proposed CFA coefficient correction minus target-minus-parent coefficients | 4 |
| Delivered mosaic | Analysis of `mosaic(output − target, colors)` | 4 |
| Delivered RGB | Analysis of `pixel_unshuffle(output − target, 2)` | 12 |

`output` includes the frozen V143 parent, overlap-synthesized proposal,
data-dependent local support and fixed signed Malvar interpolation. The RGB
packing uses four spatial phases for R, then G, then B. Thus it covers errors
at unsampled colors that delivered-mosaic supervision cannot see. The existing
physical noise/camera inputs, RAW/residual relative-frequency features,
per-bin matrix bound, smooth band and local support network are unchanged.
Targets enter the training loss, never inference or the module's forward inputs.

For either delivered arm, spectral MSE is:

```text
sum(|analysis(packed_output_error)|² / frame_scale * band)
    / (band.sum() * number_of_frames * number_of_channels)
```

The original frame size, affine removal, taper and band are retained. Each
four-phase frame-noise proxy is floored at `(16 / 65535)²`. Delivered RGB repeats
the same four values for each color. This supplies **training units, not a
calibrated post-demosaic covariance, SNR or likelihood**. Four versus twelve
channels are averaged. Moving the spectral term changes gradient direction and
effective strength, including gradients through support; the losses are not
claimed to have identical gradient norms. The spectral coefficient stays .25,
as do the delivered pixel and gradient coefficients.

The original pre-control loss delegates to the existing function without changing
arithmetic. Its trace, raw/EMA states, Adam state and all 1,644 final control
predictions must reproduce V152 relative phase exactly. This is a matched loss
comparison, not a new architecture or a continuation from trained head weights.

## Training and fixed quality coverage

All three heads start fresh and adopt the same 1,000 cached V148 batches:
4,000 old observations with the original parents, RAW, targets, noise and geometry.
Noisy-only routing gives 882 supervised batches / 3,528 observations per arm.
The 118 ADC-only batches have zero supervised gradients, while AdamW, weight
decay, momentum and EMA clocks still advance. There is no peak weighting.
Batch4, 1k updates, .001 LR, 50-step warmup, clipping1 and EMA .999 match V152.
Both pixel and gradient losses use the same 16 DN noise floor.

Ten discarded CUDA updates per arm include a genuine checkpoint at8 and restoration
of model, EMA, Adam and RNG before updates9–10. Each arm has seven supervised
and three zero-ADC steps in that check. All 39 named parameter tensors receive
finite nonzero gradients over its prefix. Production restarts fresh. The
pre-control's loss components, gradient norm and LR match the archived V152
relative-phase trace at every completed step.

All six final raw/EMA endpoints are fixed in advance, with no early epoch selection:
822 cases, 4,932 head forwards, 84 native figures and 36 repeated-cell triplets.
The review includes actual blank errors, exact quiet regions beside strong
patterns, noisy native512/256 flats, retained/organic noisy photos, ADC photos
and slopes. Response and actual target error stay separate from added change
energy. Four CFA placements are related; this adaptive reused cohort is not
a fresh blind test or 822 independent scenes.

Standing DSCF3879/3880 views retain sky, building, foliage and coarse fence.
DSCF3842/3835 cab mesh retains both windows, both noise priors and both SOOC JPEGs.
Independent ISO100/AHD/JPEG references differ in aperture, shutter, processing
and moving subjects: **qualitative references, not exact GT**, never pixelwise
scored. These captures, JPEGs, siblings and validation sources remain excluded
from training. Original media remains read-only; `/mnt/dataz` is unused.

The review controller waits on the original live training owner, then runs a
final state audit, all six endpoint collections, exact control-array audit,
scalar scoring, independent metric reductions and native rendering. Actual
native viewing is a separate required step after rendering. Native crops remain
160×160 original pixels, with identical ROI/display transforms across methods;
source, checkpoint hash, noise conditioning and exposure are recorded.

## Completed readiness checks and remaining work

Twenty-seven focused tests pass in .78s. Independent NumPy dense DFT and weighted
plane-projection operators check delivered-loss values and the full output
adjoint across all four CFAs, zero/positive frame scales, replicated borders and
nondivisible rectangular contexts. Additional tests verify exact pre-control
values/gradients, unsampled-color errors visible only to the RGB term, delivered
spectral gradients to support weights, and invalid-site rejection. They do not
establish image quality or flat safety.

Current and frozen V152 relative-phase forwards exactly match archived outputs
on 28 native256/384/512/768 contexts across CFAs and protected real controls:
56 actual compatibility evaluations. Both CUDA smoke and genuine8+2 restoration
pass; peak allocated CUDA is4.15GiB. Frozen imports pass for the training
controller and every postprocessing entrypoint. There are no new parent/DINO
calls, stochastic-noise draws, RAW decodes or original-file lookups.

The [preparation evidence](results/v153-delivered-objective-preparation-v1.json)
preserves the actual receipts, source texts, checkpoint250 audit and a timestamped
live snapshot. That snapshot is engineering/control evidence, not a final training
or quality result. RAM headroom is52GiB at launch /32GiB during work, CUDA quota
12GiB, with96GiB internal and208GiB external free-space reserves.

Final training, all endpoint scores, independent audits and actual native image
review remain pending. Useful gains and remaining weaknesses will be reported
directly, including at least two native noisy/restored/GT triplets per improved
variant and both standing real scenes. The [current model choices](current-model.md)
retain their completed measured strengths. See the
[local-time diary](../diary/2026-11-03-18-00-31-v153-delivered-spectral-objective.md).
