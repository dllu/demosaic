# V151 noisy supervision and spectral peak trial

V151 follows the [completed loss-floor comparison](objective-floor-training.md).
The tested 16 DN floor reduced several errors, but ADC steps still supplied
95.16% of a capped squared-gradient-norm proxy and fine ISO6400 wires remained
missing. Three fresh identical heads now isolate ADC supervision and a bounded
clean-spectrum weight. **Trained quality remains unmeasured.**

| Arm | Loss floor | ADC-only loss multiplier | Noisy spectral weight |
| --- | ---: | ---: | --- |
|16 DN control|16 DN|1|1|
|Noisy-only|16 DN|0|1|
|Noisy peak8|16 DN|0|`1+7*r/(1+r)`|

Here `r` is summed clean four-phase FFT power divided by summed floored
frame-noise proxies. It is a training-only target statistic, not calibrated
SNR or signal probability. The weight is in [1,8], with no renormalization.
Within supervised noisy batches, a zero clean spectrum keeps the original
penalty exactly. ADC loss removal is a separate change, measured on the same
ADC photo and sloped-field controls at inference.

## Identical inference, explicit training differences

All three heads use the same 31,409-parameter native complex matrix component
and all twelve initial tensors match. The 85 neural/inference source files are
unchanged. Physical RAW/variance/CFA/WB inputs, supplied V143 parent, frequency
band/bound, local support, constant-input handling and forward processing stay
identical. Targets and noise-condition metadata enter the training loss only.
The review executes every head on every ADC case without a bypass.

The [recipe](../configs/quality-v143-noisy-objective-v151.yaml) adopts all 1,000
V148 batches/4,000 old observations and exact cached parents. The 16 DN control
must reproduce V150's floor16 endpoint. Dataset/source distribution, domain
weights, geometry, seed, 1k horizon, LR/schedule, clipping and EMA stay fixed.
Photographs retain native 256 contexts and procedural data 512, with
bin4→geometry→area2 and no stretching/tiling to manufacture larger photo context.
The 90,782-photo/27-region eligibility and all validation/protected-source
exclusions remain unchanged.

There are 118 ADC-only batches (`shot=read=0`) and 882 noisy batches. Both zero-ADC
arms still execute all 1,000 forwards, AdamW updates and EMA updates. On ADC
steps, the loss graph produces exactly zero gradients; existing Adam moments
and weight decay can still move parameters. The optimizer/LR clock is preserved.
Thus those arms have 882 positively supervised batches/3,528 observations,
versus 1,000/4,000 for the control. They do not pretend to have1,000 supervised
batches. Peak weighting runs on 882 noisy batches only.

The original RGB pixel/gradient Charbonnier losses and pre-gate coefficient
MSE stay in place. The peak arm changes only the coefficient MSE weight relative
to noisy-only. It can favor coherent frequencies whose spatial contrast is
small; actual blank/quiet errors must establish the resulting tradeoff. No
claim of flat safety follows from its bounded weight or the matrix norm bound.

## Completed readiness checks

Thirteen objective tests passed in 1.39 s. They compare complex weighted losses
and gradients with independent NumPy reductions over all four CFAs and ADC/high
noise regimes, verify exact legacy 16 DN value/gradient reproduction and exact
baseline weights/loss for constant targets, and demonstrate zero gradients with
continued Adam motion on a zero-ADC step.

Compatibility matches the frozen trained V150 16 DN forward and archived pixels
exactly on 28 cases across native 256/384/512/768 contexts and all CFAs: 56 actual
forward-function evaluations. Each head passes ten discarded CUDA updates with
genuine 8+2 model/EMA/Adam restoration. All 12 tensors receive nonzero finite
gradients over that check; every masked ADC gradient is explicitly checked zero.
Each zero-ADC arm has seven supervised/three coasting updates in the fixed smoke
prefix. Peak weighting executes seven times. Peak allocated CUDA is 4.08 GiB.
Production restarts fresh afterward.

Checkpoint 250 contains 36 finite Adam states and finite raw/EMA tensors. Control
raw/EMA/Adam state matches V150 floor16 exactly. The preparation snapshot binds
the complete 324-row control loss/gradient/LR prefix, also exact, and 39 zero-loss/
zero-norm ADC rows per candidate. These are engineering and routing results;
they do not establish quality.

## All fixed endpoints and native comparisons

Every final raw/EMA 1k endpoint is fixed: six endpoints  × 822 cases  = 4,932 head
calls. The same 48 V150 ROI/display templates produce 84 native figures,
including 36 repeated-cell triplets. Each crop cell is 160×160 original pixels,
with shared source/ROI, noise conditioning, exposure, contrast/anchor and
checkpoint bindings across methods. The triplets are repeated pixels rather
than additional observations. There is no early epoch selection.

All noisy mesh/photo/flat controls, exact quiet regions beside strong patterns,
eight faint synthetic ADC photos and sixteen analytic ADC slopes remain.
Standing DSCF3879 ISO6400/DSCF3880 ISO100 views retain sky, building, foliage
and chain-link fence. The fine DSCF3842/3835 cab mesh retains both priors,
both windows and both camera JPEGs. Independent ISO100/AHD/JPEG references
differ in aperture, shutter, processing and motion: **qualitative references,
not exact GT**, never pixelwise scored. Both captures/siblings and all reviewed
validation sources remain excluded from training.

The reporting preflight passes 64 cached parent cases and 280 scalar checks,
maximum 1.24e-13, with CUDA uninitialized and no new neural/noise call. The
822-case cohort is adaptive reused validation, not fresh independent evidence.
There are no new parent/DINO calls, stochastic-noise draws, source/original
lookups, RAW decoding or `/mnt/dataz` access in this trial.

The [preparation evidence](results/v151-noisy-objective-preparation-v1.json)
preserves ten byte-exact receipts, frozen sources/tests, the checkpoint 250 audit
and the active 324-row snapshot with three owners confirmed live. RAM/disk
reserves and the 12 GiB CUDA quota stay enforced. Original evidence bytes remain
unchanged. Final 1k states, all endpoint arrays, independent metrics and actual
native viewing are still required. Current [inference choices](current-model.md)
retain their measured evidence; the fine-detail/clean-sky objective remains active.

See the [local-time diary](../diary/2026-11-03-16-00-12-v151-noisy-objective-trial.md).
