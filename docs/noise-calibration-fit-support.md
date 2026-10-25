# Noise estimates: ADC floors and fit support

The current metadata-backed estimator distinguishes valid negative read noise
from true ADC censoring. The RAW reader retains signed values after subtracting
black; zero in that representation is **not** the lower ADC limit. The estimator
now uses each visible CFA phase's `-black/(white-black)` floor, with half an ADC
code of tolerance for floating normalization. It still rejects actually censored,
clipped and textured patches. It never clips or modifies the input.

`noise-profile`, real-pair preparation, RAW-pair reports and automatic DNG noise
selection pass the RAW metadata. Calls without metadata retain the legacy
zero-floor convention. New profile receipts identify
`flat-patch-Haar-NNLS-ADC-floor-v2` and record phase floors/tolerances.
Existing cached data, profiles, checkpoints, executed studies and V119's frozen
training/evaluation inputs remain unchanged.

[Current implementation, retained-input check and independent audit](results/noise-calibration-adc-floor-v2.json) ·
[Real mesh conditioning comparison](gfx-green-mesh.md#fixed-nearby-capture-profile).

## Regression check on known noise

The correction was evaluated on **all 240 retained noisy inputs** from the
original synthetic study, with their hashes checked. No noisy observation or
RAW was generated again. Six known Poisson/read laws × five scene conditions ×
eight draws use native 1024 Bayer fields and ADC16/black .03. Patch 32,
maximum 4,096 candidates, bootstrap seed 42 and all rejection/fit thresholds are
unchanged. The fixed probe intensities are `.001,.005,.02,.08,.2,.6`.

| Estimator | Accepted fits | Worst tested inside-support error | Accepted fits exceeding 1dB anywhere | Worst across all probes |
| --- | ---: | ---: | ---: | ---: |
| Legacy zero floor | 192/240 | .4405dB | 55/192 | 7.0425dB |
| Metadata ADC floor | 192/240 | .6257dB | 50/192 | 7.0425dB |

All 48 narrow-range cases remain rejected. Every accepted fit remains within 1dB
at the tested intensities between its smallest and largest accepted bin means.
Those masks can change with the selected patches; this is not a matched quality
score. The corrected estimator does **not** uniformly improve variance accuracy.
The independent Python scalar calculation reproduces every recorded variance
error and support mask exactly. The calibration/conditioning/DNG subset passes
34 tests; an additional signed-RAW CLI integration test passes.

The comparison uses
`10log10((estimated_shot*x+estimated_read)/(true_shot*x+true_read))`
against the known **pre-ADC** law. Sparse probes do not validate every intensity
inside the interval. In particular, the unchanged worst case is a broad-flat
ISO100-prior draw: a small read-term error becomes +7.042dB at intensity .001,
outside its fitting support. The internal `reliable` flag describes regression
stability, **not** accuracy under deep-shadow extrapolation. Dedicated dark/flat
measurements remain stronger calibration evidence.

## Actual dark GFX context

The saved DSCF3842 mesh context has 2–11% negative samples per CFA phase, but
none at its actual ADC floor (about −.0667). Treating zero as clipping accepts
only 51 patches; the corrected convention accepts 2,134. Its accepted intensity
span is still only **.004957**, below the unchanged .05 requirement, so it
correctly refuses to identify separate shot/read coefficients.

The unchanged external DSCF3879 ISO6400 profile is more consistent with these
input-only patch statistics than the generic ISO6400 prior. That comparison is
a diagnostic: texture, signal selection and correlated noise can bias Haar
statistics. The [two-model native comparison](gfx-green-mesh.md#fixed-nearby-capture-profile)
shows more diagonal mesh texture with that one fixed external profile, while
fine lattice loss remains. Neither the statistics nor the independent ISO100
reference supply physical noise truth or a real-photo PSNR score.

## Standing DSCF3879 profile

The retained fit has accepted bin means **.007338 to .085891**, shot
`.0014635775921166604` and read variance `.0000010715704128646712`.
Existing bootstrap intervals are shot `[.001387398,.001554247]` and read variance
`[1.86218e-8,2.19451e-6]`; these are fit diagnostics. That established profile
remains unchanged, including in the main DSCF3879/3880 standing comparison.

Observed means of 256 disjoint 32×32 CFA-phase patches in each retained 512px
context give the following descriptive counts. Sampling differs from the
estimator's accepted patches; neither side of the support boundary certifies
correct or incorrect calibration.

| Context | Below minimum fit-bin mean | Above maximum | Total phase patches |
| --- | ---: | ---: | ---: |
| Sky | 0 | 0 | 256 |
| Building | 6 | 8 | 256 |
| Foliage | 104 | 0 | 256 |
| Chain-link fence | 30 | 0 | 256 |

The original independent `math.fsum` audit reproduces these 1,024 means and counts.
The [earlier V43/V63 sensitivity check](gfx-noise-conditioning-sensitivity.md)
compares ¼×/1×/4× variance: stronger conditioning softens foliage, fence and
building detail without much visible benefit in the already-clean nominal sky.
That is a separate historical sensitivity experiment.

## Preserved original study

The [original protocol and receipts](results/noise-calibration-synthetic-stress.json),
[group CSV](results/noise-calibration-synthetic-group-summary.csv) and
[exportable figure](figures/noise-calibration-fit-support.svg) describe the
**legacy zero-floor estimator**. Its original 280-array and 1,632-scalar audit
remains intact; no receipt bytes or executed numerical code were rewritten.

![Historical zero-floor estimator: variance error inside and outside fit support](images/noise-calibration-fit-support.png)

This historical figure shows median worst-probe errors across accepted draws,
with accepted counts below. It is not the corrected-estimator result.
The original `scripts/probe_noise_calibration.py` retains its no-metadata mode
for reproduction; the current 240-input correction check reuses the stored arrays.
