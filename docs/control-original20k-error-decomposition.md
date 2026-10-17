# What worsened on V63's fabric example?

Most of the selected fabric example's regression from step4,000 to the original
step20,000 endpoint is a color/coarse-error problem. In unclipped camera RGB,
**88.36% of the added MSE comes from channel-mean bias** and another10.53% from
the spatial residual remaining after four Haar reductions. In displayed sRGB,
these contributions are86.48% and12.62%, respectively. The finest two Haar error
bands improve slightly. This does not establish the cause of the error or
explain the missing fabric cords, which remain missing at both endpoints.

[Executed arrays, hashes and decomposition receipt](results/control-original20k-error-decomposition.json).
[Original endpoint report, complete source/ROI metadata and GFX crops](long-commons-v63-control-original20k-CPU-review.md).

This is a post hoc diagnosis of four previously selected exact simulated targets,
not a population estimate, a corrected-model result or a new quality gate. It
supports testing color conditioning rather than inferring increased fine-scale
smoothing from this PSNR regression alone. The
[normalization-augmentation candidate](normalization-augmentation.md) still needs
a genuine controlled GPU quality comparison after the existing original20k
reviews. No production model or inference policy changes here.

## Additive error energies

For each RGB channel, let the saved prediction error be `e = prediction − GT`
and its spatial mean be `μ`. Then:

`MSE(e) = mean_channels(μ²) + mean_pixels_channels((e − μ)²)`.

The second term is split with an orthonormal, aligned two-dimensional Haar
transform into detail energies with block supports2,4,8,16, plus the remaining
coarse energy. Every energy uses the original pixel/channel count as denominator,
so the five spatial contributions sum to the zero-mean error. These block
supports are not Fourier frequencies, recovered texture gain or a noise estimate.
In particular, an error band contains both missing signal and restoration noise.

Values below use the native256 context trimmed by eight pixels per edge. Camera
RGB is unclipped. Units are squared normalized camera values.

| Exact saved target | Total MSE4k →20k | Channel-mean MSE4k →20k | Zero-mean spatial MSE4k →20k |
| --- | ---: | ---: | ---: |
| Fabric photograph |.000230319 →.000376601|.000114868 →.000244125|.000115451 →.000132476|
| Building photograph |.000098694 →.000097773|.000000118 →.000000085|.000098575 →.000097688|
| Uniform orange |.000245669 →.000128059|.000217786 →.000098850|.000027882 →.000029209|
| Uniform magenta |.004808161 →.001145680|.004783581 →.001103881|.000024580 →.000041799|

The magenta field's large overall improvement comes from lower mean bias while
its zero-mean spatial MSE increases by70.05%. Its coarse residual worsens while
the finest two bands improve. Orange also trades a large mean-bias reduction
for a small increase in spatial MSE. These examples explain why a better flat-field
PSNR alone does not demonstrate cleaner or spatially uniform output.

All32 decompositions cover four targets ×two endpoints ×two spaces ×two regions:
unclipped linear camera RGB and clipped float64-rendered sRGB; border8 native240
and the displayed native160 ROI. The independent check uses scalar `math.fsum`
moments and differences between nested block-average energies, rather than Haar
coefficients. The largest disagreement is2.78e−17 against a fixed1e−14 bound.
Nine tests cover constant color errors, four isolated spatial bands, corrupted
band assignments and invalid geometry. Ruff passes. There are **zero new neural
forwards**, RAW reads, noise draws, fitted parameters or generated corrections.
Float64 sRGB rendering is not an exact replay of the older float32 PSNR operator.

## Native photographic context

The four original triplets below were reopened at native100% for this diagnosis.
Each panel is160×160; no pixels are resized. The columns are noisy WB-aware
Malvar, saved V63 output, and exact saved simulated GT. Source-context ROI is
`[48,48,160,160]`, CFA RGGB, WB`[2,1,1.5]`, shot`.00256`, read variance`.0000262144`,
ADC16/black`.03`, and display×1/0EV. The camera matrix and complete noise/source
metadata are unchanged and recorded in the parent report and observation NPZs.

Checkpoint SHA256:

- Step4,000: `5f29bd7efb94b72491cff22575c0565995326644823bcb802444214c8f2c6bd6`.
- Step20,000: `ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.

Fabric: [Roy Egloff, Vertigo Swiss Riviera](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg),
source`0014aa4e075b1827f91ef8a02069e1e318f040ba`,4k then20k. Mean color error
increases while the fine cords remain absent.

![Fabric4k: noisy, V63, exact saved simulated GT](images/control-original20k-CPU-crop-16593990c7d54c44.png)

![Fabric20k: noisy, V63, exact saved simulated GT](images/control-original20k-CPU-crop-daa6fb36961f0274.png)

Building: [Dietmar Rabich, Vancouver Coal Harbour](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
source`002fc6eeadf637e81d5a327f117b79abb86becd9`,4k then20k. Both outputs remain
similar, with soft clouds and small architectural details.

![Building4k: noisy, V63, exact saved simulated GT](images/control-original20k-CPU-crop-df4b3292c7b13cb3.png)

![Building20k: noisy, V63, exact saved simulated GT](images/control-original20k-CPU-crop-f5f0460ab98a35f4.png)

Both sources are[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/),
modified through binning, crop, simulated noise and restoration. Exact GT refers
to this saved simulation. No real-photo ISO100/AHD reference is scored here.

Reproduce without inference:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
uv run --no-sync python scripts/decompose_control_errors.py \
  --comparison docs/results/long-commons-v63-control-original20k-CPU-review.json \
  --sha256 e85c149629c4f7fef7b0e66e81d2a4ef5fafce8d72c0d588ab29c0987abdd24d \
  --output /mnt/external/demosaic/benchmarks/control-error-decomposition-replay
```

The output directory must be new. The completed input receipt binds the actual
checkpoint, saved float predictions, observation plans and exact targets; the
operator verifies their file hashes before analysis. Existing long-run owners,
their frozen source/data, the original427 benchmark and V43 working reference
remain unchanged. No endpoint is promoted by this diagnosis.
