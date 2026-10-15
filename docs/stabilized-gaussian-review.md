# Physical variance stabilization with a frozen Gaussian prior

This is an experimental comparison path alongside the DINOv3 model. It does
not replace reviewed V16. The independent-phase method retains more structure
in the standing GFX foliage/fence views, but loses substantial quality on the
unseen-camera development panel. Joint RGB reconstruction is being tested in
small pilots; neither result establishes state-of-the-art photographic quality.

The implementation supplies explicit nonnegative shot/read coefficients from
the same input-only calibration or nominal sensor priors used by the other
methods. It never fits weights or transform parameters to evaluation photos
and never derives gains from a reference image. Original GFX files remain
read-only and the scene/siblings stay out of training.

For shot coefficient `a > 0` and read variance `v`, the generalized Anscombe
transform maps a measurement to approximately unit noise variance. This
independent implementation uses an additive centering constant and a stable
rational expression, with float64 physical arithmetic followed by float32
neural inference and RGB output. The inverse tabulates the expected transformed
Poisson/Gaussian observation over means 0..128, then interpolates that expectation
back to signal. A continuous, matched asymptotic tail handles larger counts;
a signed linear extension handles estimates below the mean-zero endpoint.

The numerical table uses 96-node Legendre quadrature after a square-root change
of variable, removing the clipped root's endpoint singularity, and Poisson
counts 0..320. It is a numerical approximation. The published closed-form inverse
and biased algebraic inverse remain explicit diagnostic options. See
[Mäkitalo and Foi's primary paper, sections II-B and III-E/F](https://webpages.tuni.fi/foi/papers/OptGenAnscombeInverse-doublecolumn-preprint.pdf).
The inverse of an expected transformed noisy measurement differs from a plain
algebraic inverse; this matters for shadow bias.

`StabilizedGaussianPrior` applies the verified frozen grayscale DRUNet to each
original packed CFA phase, then WB-aware Malvar interpolation. Independent
phases retain native geometry. Pure Gaussian noise uses its supplied standard
deviation directly; zero stochastic noise preserves Malvar's ADC-only result.
Exactly constant phases bypass the network. The method is nonblind to its
provided physical priors and has no learned camera-specific parameters.

`JointGaussianPrior` instead alternates a closed-form CFA data-consistency step
with a frozen RGB DRUNet at native RGB resolution in stabilized camera units.
The pilot uses a short fixed schedule, motivated by the
[DPIR authors' reconstruction code](https://github.com/cszn/DPIR/blob/master/main_dpir_demosaick.py)
and [penalty schedule](https://github.com/cszn/DPIR/blob/master/utils/utils_pnp.py).
It is a new Poisson/Gaussian-domain experiment, **not a reproduction of DPIR or
Noise2VST scores**. The initial pilot has four denoising strengths 8/4/2/1 and
weight 0.23. A second pilot tests eight strengths 4→0.5 and weight 0.05 to inspect
the fidelity/noise trade-off. Parameters are fixed across images; no per-image
fitting occurs. Both pilots use only the first two named development scenes in
each panel, separately from the complete four/five-scene gray comparison.

The external neural source and original KAIR weights are checksum-verified,
loaded strictly, frozen and archived with MIT notices. The source stays outside
this repository. [Gray source/weight receipt](results/noise2vst-source-and-weights.json),
[RGB pilot source/weight receipt](results/gaussian-color-source-and-weights.json).
The [Noise2VST authors' repository](https://github.com/sherbret/Noise2VST) supplies
the inspected network implementation; its transform-fitting procedure is not
used here. No additional dependency was installed.

All 214 tests passed, including independent dense Gaussian-coordinate integration
of expected transforms, low/high-count inversion, table-boundary continuity,
sub-16-bit algebraic round-trip precision at widely differing noise ratios,
all CFA layouts, constant/ADC-only cases, CPU/CUDA arithmetic, RGB data-projection
geometry, and archived-source/weight corruption rejection. Tests use independent
properties and numerical oracles; they do not establish photographic quality.

The comparators are opt-in:

```bash
source scripts/env.sh
uv run --no-sync python scripts/evaluate_paired_raw.py /path/to/v16.pt \
  --prepared /path/to/prepared-development/manifest.json \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --gaussian-reference docs/results/noise2vst-source-and-weights.json \
  --output /mnt/external/demosaic/evaluation/gaussian-next
uv run --no-sync python scripts/report_raw_pair.py \
  configs/gfx-qualitative-20231231.json /path/to/v16.pt \
  --gaussian-reference docs/results/noise2vst-source-and-weights.json \
  --full-frame --output /mnt/external/demosaic/evaluation/gfx-gaussian-next
```

`demosaic quality` also accepts `--gaussian-reference`. Reports archive source,
frozen weights, exact conditioning and native triplets. Existing defaults and
checkpoint arithmetic are unchanged. The full gray GFX run produced complete
11662×8746×3 uint16 linear-camera-RGB and ICC sRGB files. Single shared-machine
restoration took 148.05 s, excluding decode/load/render/encoding, versus 31.35 s for
V16 in that run. This is not a controlled idle benchmark and the 10-second goal
remains unmet. All four TIFFs were verified for geometry, dtype, 16-bit sample
tags and >256 distinct sampled values; both sRGB outputs carry ICC profiles.
