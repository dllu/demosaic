# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, a pretrained DRUNet trunk, frozen DINOv3 context and tiled 16-bit output.

**Use V120 Small for general inference.** It scores 37.04008 dB on the fixed
427-photo benchmark and has verified 102MP RGB16 exports. Fine foliage, weak
mesh, neon and dark-field mottle remain weaknesses. The 100MP-in-10-seconds
speed target is still unmet.

[Model choices and tradeoffs](docs/current-model.md) ·
[PSNR history through V131](docs/performance-history.md) ·
[Research status](docs/experiments.md) · [All documentation](docs/index.md)

V131 improves the same photo benchmark by 0.04000 dB, with unseen-camera and
ADC-color regressions; an opt-in ADC repair has its own detail tradeoff.
V132's matched attention trial does not improve faint-detail quality.
[Completed comparison](docs/current-model.md#full-model-choices).
Version numbers identify experiments, not releases: V198/V200 are separate
small detail-head studies, not successors to the full V131/V132 models.

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v120-final20000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff \
  --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --batch-size 4 --precision float32 --cudnn-benchmark
```

Noise coefficients above are examples; use suitable camera/input priors.
[Usage and noise conditioning](docs/usage.md) · [DNG/JPEG export](docs/dng-export.md) ·
[Optional detail stages](docs/current-model.md#experimental-detail-components) ·
[Hot-pixel repair](docs/hot-pixel-clusters.md)

## Representative 100% crops

Noisy Malvar → **V120** → exact synthetic GT. Each cell is 160×160 unchanged
pixels; native256 RGGB context, ROI `[48,48,160,160]`, shot 0.00256/read
2.62144e−5, shared WB/matrix, exposure 1 and clipped sRGB display.
V120 checkpoint SHA256 `a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
[Source/ROI/display metadata](docs/images/v120-v121-primary-v1/manifest.json) ·
[Source credits and licenses](docs/v120-v121-primary.md#native-exact-gt-triplets).

![Bark: noisy, V120, exact synthetic GT](docs/images/v120-v121-primary-v1/crop-801b668c1c29105a.png)

![Fur: noisy, V120, exact synthetic GT](docs/images/v120-v121-primary-v1/crop-881399e7a68af49a.png)

The standing real-photo tests include sky, building, foliage and coarse fence
in the [GFX100S scene](docs/gfx-qualitative.md), plus the difficult
[green cab mesh](docs/gfx-green-mesh.md). Separate ISO100 captures are qualitative
references, not exact GT. The [Q2/Sony/GFX50R gallery](docs/cross-camera-qualitative.md)
currently covers V104/V114/V115; newer models have not been published on that panel.

## Development

Reusable data, losses, checkpoints and evaluation live in `demosaic.experiments`;
model choices and composed detail stages live in `demosaic.models`.

```bash
uv sync --extra dev --extra nonlocal
uv run demosaic-experiment models
PYTHONPATH=.:src:scripts uv run pytest -q
```

[Architecture](docs/architecture.md) · [Experiment workflow](docs/experiments.md#running-an-experiment) ·
[Training pipeline](docs/training-pipeline.md) · [Training scale and runtime review](docs/training-scale-pipeline-review-2026-11-17.md)

For research findings, use the [experiment index](docs/experiments.md) and linked
reports. Historical decisions belong in the [diary](diary/index.md).
[Documentation maintenance](docs/documentation-maintenance.md) · [Storage](docs/storage.md).
