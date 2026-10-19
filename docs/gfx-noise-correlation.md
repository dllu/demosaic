# Cached GFX noise-correlation diagnostic

The fixed GFX sky context supplies **no clear evidence for changing the current
independent-noise assumption at the tested offsets**. Its maximum absolute
correlation is .02324 across 66 Haar measurements, below the conditional
simulation 95th-percentile maxima of .02653 Gaussian/.02570 Poisson–Gaussian.
This exploratory result does not establish noise independence or calibrate the
camera. [All regions, controls, source bindings and independent audit](results/gfx-haar-noise-correlation-v1.json).

The recent [AIM RAW-denoising report](https://arxiv.org/html/2510.06601v1) emphasizes
data synthesis and training strategies, alongside architectures, and uses real
dark-frame material. Its RAW-to-RAW task and subsequent ISP differ from this
project's joint reconstruction. It motivates checking our noise assumptions;
no challenge data, code or weights are incorporated.

This probe reads the existing four cached native512 DSCF3879 ISO6400 contexts.
No original RAW is decoded; DSCF3880 is unused. Three orthonormal 2×2 Haar detail
bands operate independently on the four CFA phases. The coefficient grid has
four-sensor-pixel spacing. Tests include horizontal/vertical lags 1 and 2, plus
all six phase pairs at the same coefficient, totaling 66 measurements per crop.

Two sets of 128 simulations use a plane fitted to the same sky: independent
Gaussian noise, and independent Poisson–Gaussian noise with the existing
input-fit shot .0014635776/read variance .00000107157. These simulations omit
sensor quantization/censoring. Their quantiles describe this conditional model;
they are not measured-camera confidence intervals. Respectively 20/22 of the
128 simulated maxima are at least as large as the sky's observed maximum.

| Context | Largest absolute correlation | HH variance / existing input-prior range across phases |
| --- | ---: | ---: |
| Sky | .02324 | 1.012–1.057 |
| Building | .82542 | 1.951–2.249 |
| Foliage | .54829 | 1.316–1.595 |
| Chain-link fence | .68279 | 1.534–2.568 |

The three textured contexts mix structure with noise. Their correlations and
apparent variance excess cannot identify sensor-noise correlations; the sky
simulation is not a matched noise test for those scenes. All raw coefficients
and comparisons remain in the bound local result. No exact noise reference or
pixelwise GT is available here.

Known-noise controls verify sensitivity: planted row/column offsets yield mean
correlations .24177/.15146 against analytical .24242/.15254. The independent
white control's largest correlation is .01292. A separate einsum/corrcoef audit
reconstructs all 264 real measurements within 4.45e-16, checks saved simulation
quantiles and replays the controls. Both actual scripts exit 0 without Torch.
Input hashes remain exact. Other lags, brightnesses, frames and cameras remain
untested. Training data, noise conditioning, model and defaults are unchanged;
the standing GFX scene and siblings remain excluded from training.
