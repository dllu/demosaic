# Coupled sensor noise for matched synthetic targets

The training-data [primitive](../scripts/coupled_sensor_noise.py) samples an
aligned present/empty pair with shared Poisson counts and read noise. Each
member retains the existing sensor model's marginal distribution. The pair is
deliberately dependent, so a future difference loss could inspect weak response
with less stochastic variation between its two inputs. This is a tested data
construction, **not a trained restoration result**. V159 uses its fixed cached
inputs; this primitive has not been integrated into a training trial.

The [crossed-line source](crossed-line-training-data.md) already supplies clean
present/empty targets with identical geometry and background. Sharing a random
seed between ordinary Poisson calls does not in general define the desired
coupling across different rates. This primitive explicitly constructs the
joint law instead. The caller must use the same camera transport, exposure,
Bayer geometry and calibration on both targets before sampling sensor noise.

## Distribution and units

For nonnegative aligned sensor values `a,b`, positive shot coefficient `s` and
read variance `v`, independently draw:

```text
N0 ~ Poisson(min(a,b)/s)
Na ~ Poisson((a-min(a,b))/s)
Nb ~ Poisson((b-min(a,b))/s)
G  ~ Normal(0,v)

Ya = s*(N0+Na) + G
Yb = s*(N0+Nb) + G
```

The sum of independent Poisson variables has the sum of their rates, so each
member has mean `a` or `b` and variance `s*a+v` or `s*b+v`. Before ADC:

```text
Cov(Ya,Yb) = s*min(a,b) + v
Var(Yb-Ya) = s*abs(b-a)
```

Independent captures would instead have difference variance `s*(a+b)+2*v`.
The smaller coupled difference variance is a property of the constructed pair;
it is not a denoising gain or evidence of improved learned detail.

The implementation follows the existing 1e-12 numerical shot floor. Zero shot
uses signed clean values plus shared Gaussian read noise. Positive shot counts
clamp negative signals to zero and count overexposure before clipping, matching
the existing model. Both members then use the same black-level transform,
clipping and 8–16-bit ADC quantization. The equations above describe pre-ADC
moments; clipping/rounding can change those moments. Inputs are finite FP32
tensors; noise/calibration coefficients broadcast over the shared shape.

Identical target pixels share exactly identical noisy values, including empty
pixels outside a changed mesh mask. Explicit local generators reproduce the
pair without advancing global RNG state. RNG consumption differs from two
independent calls; old cached observations are never replaced by this construction.

## Completed checks and remaining experiment

**16 CPU tests pass in 1.02s.** Independent analytic checks cover pre-ADC means,
variances, covariance and difference variance; a low-electron test compares the
entire sampled count histograms with Poisson PMFs. Further cases check exact
empty-mask equality, explicit ADC calibration/overexposure, coefficient
broadcasting, local RNG reproducibility and invalid-input rejection before draws.

The separate [audit](results/coupled-counterfactual-noise-v1.json) retains four
262,144-sample pairs, their actual noisy/pre-ADC arrays, seeds and byte-frozen
source/test/sensor-model texts. Exact constructed sensor levels are .02/.024,
16-bit ADC, zero black level. Difference variances are:

| Prior | Analytic pre-ADC difference variance | Observed |
| --- | ---: | ---: |
| ISO100 | 8.000000e-8 | 7.995328e-8 |
| ISO6400 | 5.120000e-6 | 5.118787e-6 |
| ISO12800 | 1.024000e-5 | 1.023545e-5 |
| ADC only | 0 | 0 |

These fixtures use 12 Poisson and four Gaussian sampler calls, excluding unit
tests. There are no model forwards, updates, source-image lookups or RAW decodes.
Protected media and `/mnt/dataz` remain unused.

A future matched trial could retain identical paired data in both arms and add
one fixed loss on `(F(Ya)-F(Yb))-(Ta-Tb)` to one arm. Each forward would still
see one noisy image. Paired-response supervision might also amplify unwanted
noise sensitivity; ordinary RGB, actual quiet/blank/DC/spatial errors, native
flats, natural material and both standing real fence scenes remain required.
No paired training, checkpoint or quality improvement is claimed here.

[Local-time diary](../diary/2026-11-07-02-22-11-coupled-counterfactual-noise.md).
