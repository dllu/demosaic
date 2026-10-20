# Fixed V88/V89 measured-RAW spectral comparison

This experiment tests whether coherent input Fourier evidence can recover weak
detail that the mature RGB restoration suppresses. V88 retains genuine V63
original20k EMA; V89 adds a zero-initialized68-parameter residual gate. Both
fresh arms train4,000 updates. No result or promotion is assumed.

## Intervention

An orthonormal real Fourier transform operates independently on four measured
CFA phases. Sum the phase powers normalized by each phase's spatial mean input
variance, S. With M packed pixels, t=log(M/.01) and
T=4+4sqrt(t)+2t, the shared mask is max(1−T/S,0), with DC exactly zero.
Its correction is inverseFFT(mask×FFT(observed−mosaic(parent RGB))), followed
by signed linear Malvar reconstruction using the existing CFA and WB.
The complete model adds tanh(w×mean(decoder features, predicted normalized RGB)+b)
times this correction. The scalar gate shares all RGB channels/spatial sites.
No target, known carrier frequency, selected ROI, input clipping or rounded
export enters the forward. There is no new DINO encoding.

For known independent Gaussian pixel noise, the normalized coefficient quadratic
has trace4 and operator norm at most1; a conservative Gaussian quadratic/union
bound motivates T. Actual Poisson noise, ADC quantization and observed-signal
variance proxies do not inherit a calibrated false-discovery guarantee. The
1e-12 phase-variance floor is explicit finite arithmetic, not measured ADC noise.
Periodicity, tile-size dependence, boundary leakage, over-suppression and false
patterns are risks to test. Zero phase DC before Malvar does not guarantee an
exact zero mean in each interpolated RGB channel at borders.

The new head draws no RNG and starts exactly at zero. Existing model outputs
and common gradients must match at initialization. Its LR multiplier is20
while the common model retains1e-5; this permits a fresh zero gate to learn
within a short mature-model fine-tune. This architecture plus its head optimizer
is the intervention; it is not an optimizer-only or equal-compute comparison.
All existing inference and training defaults stay off.

## Common training data and schedule

Both arms use the newly reviewed88,508 Commons training sources from
`commons-post4557-reviewed-20261020-v1/manifest4.jsonl`, native128 captures/106
groups and paired32 scenes. The old validation/test memberships stay fixed.
Admission includes source/cache/duplicate/title/DINO/manual checks, with known
ambiguities withheld; finite checks do not establish complete scene independence.
This trial does not isolate the effect of data expansion versus earlier trials.
Future private150/public-RAW18 extensions remain inactive. Cached GFX3879/3880
and their siblings remain excluded from training. Original captures are read-only.

Common recipe: native256/B16, seed55, BF16/channels-last, strict deterministic
execution, official frozen DINOv3 ConvNeXt-Tiny, sensor-valid physical targets,
Charbonnier losses, .25native/.25paired fractions, existing physical shot/read
noise and negative read noise, flat/procedural palette,4×→geometry/PSF→area2,
LR1e-5/warmup100/cosine4000/10%floor. Each arm draws64,000 examples.
Initialize from original V63 EMA SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
There is no larger context or supervised area, new noise distribution, changed
target or additional spectrum-specific training loss.

Record actual forward/source/loss hashes at steps1–16 and every25 thereafter;
require matched domains/base LRs and final Python/CPU/CUDA RNG. Check full
model/EMA/AdamW finite states, counters and source archives. These observations
do not independently replay every unrecorded sample. Retain1000/4000 endpoints
for integrity; only original4000 endpoints enter the final comparison. Routine
validation cannot select, shorten, extend or promote a trial.

## Engineering and review requirements

Independent dense complex DFT, signed/WB camera units, all Bayer/D4 geometries,
odd rectangular fields, separate batch equivalence, complex backward, constant
and ADC arithmetic, complete parent values/common gradients/RNG and checkpoint
reload must pass. Genuine CPU/B1/native64/FP32 and CUDA/B16/native256/BF16
16-update mixed-domain checks must pass, including uninterrupted versus8+8
whole-state restart for the new branch. Engineering weights are discarded and
retain the original4000 LR horizon. They are not quality or throughput results.

Run one arm at a time with48GiB available for60s before full training,24GiB CUDA
quota, root128GiB/external500GiB reserves,14,400s arm and resource-wait bounds.
Stop only the exact owned worker on24GiB remaining RAM, disk reserve or runtime
failure. Preserve failures and existing checkpoints; no automatic retry/extension.

Fresh final FP32 evaluation uses unchanged known4/unseen5/full427 photographic
and16 procedural sources, all seven conditions/four CFAs, canonical camera-linear
scores,418/416-source sensitivities, analytic/ADC/hue/highlight panels, and
V43/RawNIND references with matching classical/source witnesses. All fixed native
boards must actually be viewed before numerical decisions. Keep unfavorable
conditions and groups. AHD and GFX ISO100 references are not exact RGB GT.

A matched benefit requires a positive lower95% source-bootstrap photographic
PSNR bound, known/unseen losses at most.03dB, and no new visible failure.
Weak-detail benefit requires at least+.05 signed gain in both existing high-noise
cases, flat spatial-luma RMS at most1.25×control, and no individual ADC gain loss
greater than.05 across all192 layout/draw cases. Keep all12 ADC group means.
Each endpoint independently requires at least+.05dB over fresh V63 on photo,
known4 and unseen5 with positive95% lower bounds and photo-SSIM loss≤.0001,
plus complete native review, before full-frame eligibility. These numerical
criteria do not establish SOTA or automatic promotion. One seed/source bootstrap
does not measure training-repeat uncertainty.

Reports need at least two native160 noisy/restored/exact-GT triplets per model,
matching source/ROI/noise/color/exposure and checkpoint hashes, plus GFX sky,
building, foliage, fence and illuminated sign/platform views. Never resize crop
pixels or fit display exposure by method. No qualitative-scene tuning, protected
final scoring, new full-frame/speed claim or default change follows automatically.
