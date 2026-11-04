# V152: relative RAW/residual phase trial

V152 tests a missing input to the late frequency estimator after the
[completed noisy-only comparison](noisy-objective-training.md). V151 modestly
improved synthetic mesh response and noisy-flat errors, but real cab wires,
natural texture and exact quiet-region errors remained weak. **V152 trained
quality is still unmeasured.**

## The specific representation gap

Let `O` be the observed four-phase RAW spectrum and `I = O - P` its innovation
against the sampled V143 parent. The existing frequency network receives
separate normalized Gram descriptors of `O` and `I`, plus CFA/frequency
coordinates. The descriptor of `I` is exactly unchanged by `I → -I`; the
frequency matrix therefore cannot distinguish that relative-phase reversal
from those descriptors. This is a statement about the frequency estimator.
The complete model's spatial-support path also sees RAW, parent and proposal
and can carry other evidence; the test does not prove whole-model ambiguity or
useful recoverability from a particular noisy capture.

The new head adds eight same-site cross-spectrum coordinates:

```text
n = sum_phase(frame_noise_proxy)
z_i = O_i * conjugate(I_i)
scale = sqrt(max(sum(abs(O)^2)+n, 1e-12)
             * max(sum(abs(I)^2)+n, 1e-12))
relative8 = concatenate(real(z)/scale, imag(z)/scale)
hidden = original_conv48(original_features) + zero_init_conv8(relative8)
```

These input-only features distinguish the residual reversal while remaining
invariant to a common complex phase rotation. Their normalization is not
calibrated coherence, SNR, detection probability or a flat-safety guarantee.
There is no target/reference argument in the new feature function or forward.

The bias-free circular 3×3 adapter maps eight channels into the existing
32-channel hidden layer, before the original SiLU. It adds 2,304 parameters:
33,713 / thirteen tensors versus the native control's 31,409 / twelve.
All twelve common initial tensors match; the adapter starts zero. Loading any
trained native head with a zero adapter embeds its outputs exactly in the
tested CPU/CUDA cases. Input evidence and parameter count change together, so
an eventual gain would not isolate one causal mechanism.

The original 85 neural files remain byte-identical; the new
[research module](../src/demosaic/late_spectral_relative.py) is the sole neural
addition. Physical arguments, affine removal/taper/FFT geometry, radial band,
complex norm projection, spatial-support architecture and signed Malvar
interpolation are inherited. The existing constant-CFA inactivity property
remains tested, without implying general safety on noisy or sloped flats.

## Fixed matched training and quality review

The [recipe](../configs/quality-v143-relative-phase-v152.yaml) compares fresh
`noisy-control` and `relative-phase` heads on all 1,000 existing V148 batches /
4,000 observations and exact V143 parents. Both use V151's noisy-only objective:
16 DN floor, zero ADC-only total-loss multiplier, no peak weighting. There are
882 supervised batches / 3,528 observations per arm. All 1,000 forward, AdamW,
EMA and learning-rate clocks remain; 118 ADC steps have zero gradients but
existing moments and weight decay coast. Dataset/geometry/domain weights,
common initialization, LR/schedule/clipping, EMA and 1k horizon otherwise match.

Photographs retain native256 contexts, procedures native512, and the original
bin4→geometry→area2 pipeline. The 90,782-photo/27-region eligibility and all
validation/protected-source exclusions remain. No new parent/DINO call,
stochastic-noise draw, source/original lookup, RAW decode or `/mnt/dataz` access
is needed. All existing evidence and originals are preserved.

All four final raw/EMA endpoints are fixed before training: 822 cases × four
heads = 3,288 review forwards, with 4,686 scored rows including retained parents
and periodic-detail outputs. The native control must reproduce V151 noisy-only
trace, raw/EMA/Adam state and all 1,644 raw/EMA prediction arrays exactly.
There is no early epoch selection.

The same 48 fixed ROI/display boards produce 72 native figures, including
24 repeated-cell triplets, in 18 unscaled sheets. Every cell is 160×160
original pixels with identical ROI, noise conditioning and display transform
across methods; checkpoint/source hashes and exposure are recorded. The cohort
is adaptive reused validation, not fresh independent evidence.

All noisy mesh/photo/flat controls, actual blank errors, quiet regions beside
strong patterns, ADC photos and analytic ADC slopes remain. Standing
DSCF3879 ISO6400 / DSCF3880 ISO100 views retain sky, building, foliage and coarse
fence. DSCF3842/3835 fine cab mesh retains both priors, both windows and both
camera JPEGs. Independent ISO100/AHD/JPEG references differ in aperture,
shutter, processing and motion: **qualitative references, not exact GT**,
never pixelwise scored. Both captures, JPEGs and siblings remain out of training.

## Completed readiness checks

Ten focused tests pass in 1.06 s: independent NumPy feature values and finite
difference complex gradients in ADC/high-noise regimes, the marginal-descriptor
alias and relative-feature distinction, common-phase invariance, exact trained
native embedding across all four CFAs, arbitrary learned constant-CFA behavior,
full learned matrix reconstruction with NumPy, constructor/RNG/meta handling
and finite zero-spectrum derivatives.

Compatibility passes 28 cached contexts across native256/384/512/768, all CFAs
and protected real controls. Current native, frozen base forward, zero-adapter
embedding and archived V151 noisy-only outputs agree exactly: 84 actual
forward-function evaluations. Both heads complete ten discarded CUDA updates
with genuine 8+2 model/EMA/Adam restoration. All 25 tensors receive finite
nonzero gradients over the prefix; both heads have seven supervised and three
zero-ADC updates. Peak allocated CUDA is 4.15 GiB. Production starts fresh.

The reporting preflight passes 64 cached parent cases and 280 independent
scalar checks, maximum 1.78e-15, with CUDA uninitialized and zero new neural or
noise calls. The first controller bootstrap exited before imports/claim/work
because its relative import path resolved from the wrong working directory.
Its exact terminal owner/log are preserved; an absolute frozen import path
starts the valid controller. No scientific phase or worker was restarted.

Checkpoint 250 has finite raw/EMA tensors and all 25 finite Adam states. Native
control raw weights, EMA and Adam state exactly reproduce V151 noisy-only.
The [preparation evidence](results/v152-relative-phase-preparation-v1.json)
preserves eleven byte-exact receipts and fourteen source texts, the 86 frozen
neural hashes and unchanged previous 85. Its historical active snapshot has
397 complete exact-control trace rows, 46 zero-loss/zero-norm ADC rows per arm
and all three current owners confirmed live by PID/create time. These checks
establish control/routing behavior, not quality.

Final trained quality, independent endpoint metrics and actual native viewing
remain required. The requested fine-detail/clean-sky objective is active.
See the [local-time diary](../diary/2026-11-03-16-45-21-v152-relative-phase-estimator.md).
