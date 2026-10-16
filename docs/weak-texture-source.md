# Experimental continuous-precision weak textures

The prepared generator supplies bounded low-contrast targets without an8-bit
raster intermediate. It is available through a default-off training option;
active recipes retain their original data. No trained-model
improvement follows from generating clean fields or passing engineering tests.
[Actual32-sample CPU preparation receipt](results/weak-texture-source-preflight.json).

`demosaic.textures.weak_texture(size, rng, pixel_scale=1, kind=None)` returns
scene-linear float32 RGB and a complete seed/parameter recipe. Modes are
isotropic band-limited random fields and curved, multi-frequency fibers.
Background levels span2⁻⁸–.5, peak relative contrast .005–.2, with a constant
color tint. Measured RMS contrast is recorded separately from the peak value.
No camera rendering, CFA, sensor noise or inferred image detail enters these
clean targets. These two modes are an independent experimental construction.

Frequencies use final sensor-pixel units. For the current pre-downsample
augmentation convention, generate512px at `pixel_scale=2`, perform the existing
geometry/optical PSF operations, and finally area-average2×2 to native256px.
No geometry follows that reduction. The random-field passband ends below.22
cycles/final pixel. This is a generator support constraint, not a claim that
later geometry/PSFs preserve an ideal band limit.

The actual CPU preflight produces16 fields per mode and passes them through
the current augmentation function. All32 outputs are finite, positive float32
RGB at256px. Before geometry/PSF, area2 retains98.20–99.86% of the input RMS
contrast. Input/area2/augmented tensor hashes, recipe parameters and four full
float32 NPZ fixtures are archived. Quantized code counts are descriptive;
continuous analytic values do not imply that many independent sensor bits.

Observed median generation time after the first two fields was7.85ms for the
band-limited mode and2.73ms for fibers, using two CPU threads while other work
ran. Augmentation medians were3.70/4.56ms. These are execution observations,
not isolated throughput measurements or a measured training-speed gain.
CUDA was never initialized.

Seven targeted tests verify deterministic output, unchanged Python/Torch global
RNG, valid linear range, continuous levels, final-pixel frequency units and
invalid-parameter rejection. The model-response diagnostic separately tests
signed coherent contrast and unrelated residual energy on exact analytic
targets. Any eventual training trial must preserve the photo/flat allocation,
use a matched control, check flat false detail and repeat native/full/GFX review.

## Optional training routing

Set `weak_texture_fraction: 0.1` alongside `synthetic_fraction: 0.2` and
`augmentation_downsample: 2`. This replaces half the existing procedural quota,
keeping photographic and flat probabilities unchanged. With the25/25/50 paired/
native/Commons mix, weak fields occupy an expected5% of all patches. Native
and registered paired data do not change. The default is0, and validation
always disables procedural sources. Geometry/PSFs still precede final area2.

Routing selects the source before generation or photo IO. Weak draws do not
load a Commons photo or generate a discarded strong-shape image. Resume rejects
changed weak, strong-procedural-total or flat fractions. A worker-spawn fixture
with all-weak training produces identical full/resumed model and EMA tensors.

[Actual frozen-loader compatibility](results/weak-texture-routing-parity.json):
all20 declared seed52/native256 samples match frozenb62c996 exactly at the
default. Enabling.1 changes only the five declared replacement samples;
photo/flat/remaining strong-procedural samples stay exact. These finite samples
are compatibility evidence, not a full-epoch proof or a model-quality result.

[Prepared V55](../configs/dino-paired-weak-texture-b16-v55.yaml) keeps the V54
reviewed83-ID corpus, identical V43 step2000 initializer, seed52/B16/LR3e-5/
planned4000 schedule and all model/loss/noise/inference flags. Only the weak
quota and run/notes differ. The current4000-step quality workflow runs in its
unchanged frozen source. New-source CUDA/genuine-parent preflight must wait
for that owner's actual exit; V55 quality training has not started.

[Hybrid texture-acutance training research](https://arxiv.org/html/2404.07212v1)
motivates separate texture checks; this code does not reproduce its dead-leaves
generator, acutance loss or reported scores. The broader
[research record](research.md#texture-retention-and-training-scale-follow-up)
records the scope and recent RAW training context.

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' uv run --no-sync python scripts/preflight_weak_textures.py \
  --output /mnt/external/demosaic/benchmarks/weak-texture-source-replay
```
