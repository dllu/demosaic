# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 features and tiled 16-bit TIFF output on NVIDIA GB10.
**V43 step 2000 remains the working experimental reference.** Later models often
score higher PSNR, but have not established better overall real-photo quality
and fine-detail recovery. State-of-the-art quality and 100 MP in 10 s remain open.

Current work returns to **V43's architecture**: visually clean the larger
Commons corpus, reduce blur augmentation, and train with more low-contrast fine
detail. See the [quality plan](docs/quality-first-training.md),
[experiment index](docs/experiments.md) and [documentation guide](docs/index.md).

![PSNR versus model version](docs/images/version-PSNR-history.png)

[PSNR history, data and limitations](docs/performance-history.md). Version numbers
name different experiments with unequal training budgets; these are descriptive
results, not a controlled architecture ranking.

## Current 100% crops

Noisy → V43 → exact synthetic GT. Each panel is native 160×160 at the 8×-binned
evaluation resolution, with fixed ISO12800 noise and shared display transforms.
Fine cords and texture are still lost. [Source, ROI, checkpoint, noise and display
metadata](docs/mature-cudnn-fullframe.md).

![Fabric: noisy, restored and exact synthetic GT](docs/images/mature-cudnn-GT-v43-0014aa4e.png)

![Building and sky: noisy, restored and exact synthetic GT](docs/images/mature-cudnn-GT-v43-002fc6ee.png)

Sources: [Roy Egloff](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg)
and [Dietmar Rabich](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by binning,
crop, simulated noise and restoration.

Real GFX100S: DSCF3879 ISO 6400 → V43 → DSCF3880 ISO 100 f/5.6, native 160×160
sensor pixels and shared +2 EV display. The last panel is an independent
qualitative reference, **not GT**: aperture and moving subjects differ.
[All four standing regions](docs/mature-cudnn-fullframe.md) ·
[colored lights](docs/gfx-highlight-qualitative.md) ·
[other cameras and RawNIND comparisons](docs/cross-camera-qualitative.md).

![GFX foliage: noisy, restored and separate low-ISO reference](docs/images/mature-cudnn-fullframe-v43-foliage.png)

![GFX fence: noisy, restored and separate low-ISO reference](docs/images/mature-cudnn-fullframe-v43-chain-link-fence.png)

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v43-step2000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff \
  --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --batch-size 4 --precision float32 --cudnn-benchmark
PYTHONPATH=.:src:scripts uv run pytest -q
```

The noise values are examples; use appropriate camera/input priors.
[Usage and training](docs/usage.md) · [data pipeline](docs/training-pipeline.md) ·
[evaluation](docs/evaluation.md) · [research](docs/research.md) ·
[local-time diary](diary/index.md). Speed experiments are deferred while quality
work proceeds; existing [full-frame validation](docs/mature-cudnn-fullframe.md)
remains available.
