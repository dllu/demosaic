# V154: more relative pressure on weak delivered spectral errors

This active matched trial follows the [completed V153 comparison](delivered-spectral-objective.md).
Delivered-output MSE gained synthetic mesh response, but real crossings and
organic texture stayed missing, with worse blank/natural/ADC behavior. V154
changes the penalty on the same delivered RGB spectral error.
**Restoration quality is not measured yet.**

The hypothesis is that quadratic spectral error gives weak coefficients too
little pressure relative to larger errors. A smooth robust penalty increases
their relative gradient without a clean-target-power mask. Erroneous band
coefficients in flat targets remain penalized. It also reduces relative pressure
on large errors, so actual blank/quiet error must be measured directly.

## Three fixed objectives

The [recipe](../configs/quality-v143-robust-spectral-v154.yaml) fixes three fresh
identical relative-phase heads: 33,713 parameters in 13 tensors. All 86 neural
source files and inference inputs remain unchanged.

| Arm | Delivered RGB spectral penalty | Epsilon in proxy units |
| --- | --- | ---: |
| MSE control | `r²` | 0 |
| Charb .01 | `sqrt(r² + ε²) − ε` | .01 |
| Charb .003 | `sqrt(r² + ε²) − ε` | .003 |

`r² = |analysis(pixel_unshuffle(output − target, 2))|² / frame_scale`.
The output includes the parent, overlap synthesis, spatial support and signed
Malvar interpolation. Four spatial phases for R, then G, then B cover all 12
camera-RGB phases, including unsampled colors.

The robust function uses `r² / (sqrt(r² + ε²) + ε)` to avoid cancellation for
tiny powers. Zero error gives zero value and complex-error gradient, with finite
derivatives. Relative to MSE, each nonzero coefficient's gradient magnitude is
multiplied by `1 / (2 * sqrt(r² + ε²))`. This is a coefficient-level comparison,
not a claim about the total neural gradient norm or quality.

Analysis size, taper, affine removal, smooth band and averaging over frames,
channels and band bins match V153. RAW frame-noise scales are repeated for each
color and floored at `(16 / 65535)²`: **training units, not calibrated RGB
covariance, SNR or detection probability**. Epsilons are in these proxy units,
not fixed pixel-DN thresholds. Affine/DC and frequencies outside the band remain
outside this term; unchanged RGB pixel loss still penalizes those output errors.

The spectral coefficient stays .25. Pixel/gradient terms, physical conditioning,
input evidence, matrix bound, support, initialization, data/geometry/domain
weights, clipping, LR and EMA match. Penalty shape and effective gradient strength
change together. Targets enter training losses, never forward. The MSE branch
delegates to the old function without changing arithmetic and must reproduce
V153 delivered-RGB trace, raw/EMA/Adam states and all 1,644 control arrays exactly.

## Fixed data and review

Each head adopts the same 1,000 cached V148 batches / 4,000 old observations,
with original RAW, parents, targets, conditioning and noise. There are 882
supervised batches / 3,528 observations and 118 zero-ADC-gradient batches. All
1,000 AdamW/EMA clocks advance, including momentum/weight-decay coasting.
Batch4, 1k updates, .001 LR, 50-step warmup, clipping1 and EMA .999 match V153;
there is no peak weighting.

Three discarded ten-update CUDA checks include genuine8+2 model/EMA/Adam/RNG
restoration. Production starts fresh. Six final raw/EMA endpoints are fixed in
advance, without early epoch selection: 822 cases, 4,932 head calls, 84 native
figures and 36 repeated-cell triplets. Actual blank/quiet errors, noisy flats,
natural response, ADC photos/slopes and whole-scene errors remain separate.
Four CFA placements are related; this adaptive reused cohort is not a fresh
blind test or 822 independent scenes.

Standing DSCF3879/3880 views retain sky, building, foliage and coarse fence.
DSCF3842/3835 cab mesh retains both windows, both priors and both SOOC JPEGs.
Independent ISO100/AHD/JPEG references differ in aperture, shutter, processing
and motion: **qualitative references, not exact GT**, never pixelwise scored.
Captures, JPEGs, siblings and validation sources stay excluded from training.
Original media remains read-only; `/mnt/dataz` is unused.

The queued reviewer runs final state audit, mandatory actual-checkpoint validation
with strict CPU loads, all six collections, exact-control array audit, scores,
independent metrics and native rendering. This carries forward V153's reviewer
correction and retains failed-child metadata. Actual native viewing follows
rendering. Crop cells stay160×160 original pixels with identical ROI/transforms
and recorded checkpoint/source hashes, conditioning and exposure.

## Completed readiness and storage checks

Twenty-seven focused tests pass in .80s. Independent NumPy dense-DFT/weighted-plane
operators check both robust losses and full output adjoints on two-image,
nondivisible rectangular batches, across four CFAs and zero/positive scales.
Other checks cover exact MSE values/gradients, tiny complex errors, finite first
and second derivatives at zero power, weak-error pressure, flat-target and
unsampled-color penalties, support gradients and invalid epsilons. These are
objective/operator checks, not quality or flat-safety proof.

Current and frozen V153 forwards match archived outputs on 28 native256/384/512/
768 contexts: 56 actual evaluations. All three CUDA checks pass with seven
supervised / three zero-ADC steps each; all39 tensors receive finite nonzero
gradients over the prefix. Peak allocated CUDA is4.15GiB. Production is active,
with exact MSE-control component/norm/LR replay at every completed step.
All six frozen postprocessing entrypoints pass import preflight.

Two MSE-control endpoints require4.421GiB locally; four robust endpoints require
8.842GiB on the external SSD. Initial free space was108.56/222.45GiB on separate
filesystems. This retains96/208GiB reserves without moving or deleting evidence.
Every prediction/export records its actual path/hash. RAM headroom is52GiB at
launch /32GiB runtime and CUDA quota12GiB. No new parent/DINO calls, noise draws,
original lookups or RAW decodes occur.

The [preparation evidence](results/v154-robust-spectral-preparation-v1.json)
preserves actual receipts, source texts, checkpoint250 audit and a timestamped
live snapshot. This is engineering/control evidence. Final training, all six
endpoint scores, independent quality audits and actual native viewing remain
pending. Gains and remaining weaknesses will be reported directly, with two
native noisy/restored/GT triplets per improved endpoint and both real scenes.
Existing [model choices](current-model.md) retain their measured strengths.
See the [local-time diary](../diary/2026-11-03-18-55-27-v154-robust-spectral-objective.md).
