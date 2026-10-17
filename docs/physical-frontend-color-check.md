# Bright-field bias and the physical preprocessing

The normalization round trip does not explain the large learned color shifts
on the fixed hue grid. A CPU-only diagnostic of all 1,176 fields finds at most
**7.93e-6 camera-RGB mean error with ADC-only input**, versus roughly .06–.09
worst bright-field bias in the trained first1k arms. With the high-noise prior,
the explicitly uniform-field physical mean estimator has maximum error .001056,
while learned bright-field errors reach about .121.

[Execution, source hashes, all groups and review preparation](results/palette-final-review-preparation.json).
[Diagnostic script](../scripts/probe_color_grid_physical_frontend.py).
[Frozen hue grid and native model previews](wide-flat-palette-first1k-review.md).

The check rebuilds production GAT, Malvar and affine normalization on the
original observations. It then undoes normalization without a CNN. Separately,
it spatially averages the transformed Malvar field over the same native
ROI [48,48,160,160] and applies the production expectation-based GAT inverse.
That second operation **assumes a uniform scene**. The raw per-color CFA mean
is another uniform-scene estimator. Neither is a proposed photographic
denoiser, learned-output correction or fitted target transform.

| Input condition | Cases | Largest uniform physical-mean error | Largest direct CFA-mean error | Largest normalization round-trip error |
| --- | ---: | ---: | ---: | ---: |
| ADC-only | 588 | .000007927 | .000007868 | 5.97e-8 |
| High-noise protocol prior | 588 | .001055598 | .001082825 | 3.82e-6 |

Mean errors use normalized camera RGB, maximized over channels and cases.
The last column is in transformed coordinates for the high-noise condition;
it is not a camera-RGB error. The high-noise prior is shot=.00256 and read
variance=.0000262144. Both conditions retain ADC16/black .03. All clean fields
are spatially constant and below white; noisy ADC can clip. No new noise was
drawn, photograph decoded, neural network loaded or CUDA context created.

Independent NumPy64 evaluation of the centered GAT forward expression and
scalar inverse interpolation agrees exactly after F32 conversion on these
inputs. The inverse comparison uses the same numerical expectation table;
it does not independently validate that table's theoretical derivation.
All source/case labels, source hashes and finite values are checked; individual
scalar results remain on the external SSD.

This narrows the diagnosis: large errors appear after learned reconstruction,
while the direct affine round trip is numerically accurate. It does not identify
why training develops those errors, exclude interactions with the transformed
features, or establish a general color repair. The matched palette trial still
needs its planned 4,000-update review. Existing optional multiscale sensor losses
are already implemented; this check does not introduce a duplicate loss or
change either running arm.
