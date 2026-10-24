# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 features and tiled 16-bit TIFF output on NVIDIA GB10.
**V104 final20k is the working quality baseline for positive-noise captures and
continued training**, using V84's pretrained DRUNet RGB trunk and frozen DINOv3
ConvNeXt-Tiny pyramid. It reaches **36.801dB** on the full 427-photo panel:
+.121dB over V102 and about +1.90dB over V43, with 424/427 source means improving.
Known-camera and weak-texture scores improve; V102 retains lower ADC flat-color
bias and a higher unseen-camera mean.
[Completed results, native comparisons and tradeoffs](docs/v104-reviewed-corpus-quality.md).

V104 completed 20k updates on 90,872 sources, all seven evaluation panels and
complete 102MP GFX exports. Fine high-noise texture and real foliage still need work.
The next [matched loss-scale test](docs/loss-scale-training.md) uses V104 and
90,864 cleaned sources to test faint-detail supervision: V111 is training and
V112 is queued. The separate
[Tiny/Small recipes](docs/convnext-small-capacity.md#prepared-matched-quality-trial)
remain prepared.
[Current models](docs/current-model.md) · [Source-quality review](docs/incoming-commons-quality.md) ·
[Historical diary](diary/index.md).
For explicit zero-shot/read inputs, [optional site consistency](docs/adc-consistency.md)
adds **.40dB ADC-only PSNR** with unchanged V84 weights across all427 photos/four
CFAs; positive-noise inputs bypass it. The report includes native crops and color tradeoffs.
The [V104 ADC diagnostics](docs/v104-adc-color-projection.md) show color/texture
tradeoffs; its full photographic comparison is running.

![PSNR versus model version](docs/images/version-PSNR-history.png)

[PSNR history and full values](docs/performance-history.md). Versions have unequal
training budgets and data; this describes available models rather than an
isolated architecture ablation.

## Current 100% crops

Noisy observation → **V104 final20k** → exact synthetic GT, at the ISO100 prior.
These are unchanged 160×160 crops at the 8×-binned evaluation resolution, with
shared coordinates and display transforms. V104 gains +.166dB over V102 on the
four selected ISO100 contexts; high-noise detail remains soft.
[Compare V102,V104 and RawNIND](docs/heldout-detail.md) ·
[source/ROI/checkpoint/noise/display metadata](docs/images/detail-v102-v104/iso100-prior/manifest.json).

![V104 final20k, bark: noisy, restored and exact synthetic GT](docs/images/detail-v102-v104/iso100-prior/V104-0ae232278265.png)

![V104 final20k, canopy: noisy, restored and exact synthetic GT](docs/images/detail-v102-v104/iso100-prior/V104-212ae12913ef.png)

Sources: [Derek Ramsey](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/), and
[Grendelkhan](https://commons.wikimedia.org/wiki/File:Forest_covered_hills_on_Yakushima.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by binning,
cropping, simulated noise and restoration.

Real GFX100S: DSCF3879 ISO 6400 → **V104 final20k** → DSCF3880 ISO 100 f/5.6. Native160
sensor-pixel crops from complete102MP blended outputs, with shared +2EV display. The last
panel is a separately captured qualitative reference, **not GT**.
[Compare complete102MP V102/V104/RawNIND outputs](docs/gfx-qualitative.md).
Real-photo changes remain small; fine foliage and saturated-light detail still need work.
The [Q2, Sony a7R II and GFX50R gallery](docs/cross-camera-qualitative.md)
also compares V102/V104 on six fixed native regions; changes remain small.
[V104 conditioning controls](docs/noise-conditioning.md) illustrate the
tradeoff between retained detail and residual grain.

![V104 final20k GFX foliage: noisy, restored and separate low-ISO reference](docs/images/gfx-v102-v104-fullframe/V104-foliage.png)

![V104 final20k GFX fence: noisy, restored and separate low-ISO reference](docs/images/gfx-v102-v104-fullframe/V104-chain-link-fence.png)

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v104-final20000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff \
  --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --batch-size 4 --precision float32 --cudnn-benchmark
PYTHONPATH=.:src:scripts uv run pytest -q
```

Noise values are examples; use suitable camera/input priors.
[Linear DNG + full-resolution JPEG batch export](docs/dng-export.md) preserves
camera RGB and adapts existing darktable XMP edits. Add `--hot-pixels` to repair
isolated Bayer defects before restoration.
`--hot-pixel-clusters` also handles paired same-color defects; see the
[native crop investigation](docs/hot-pixel-clusters.md).
[Usage](docs/usage.md) · [current training](docs/quality-first-training.md) ·
[data pipeline](docs/training-pipeline.md) · [experiments](docs/experiments.md) ·
[documentation guide](docs/index.md). Quality takes priority. State-of-the-art
quality and 100MP within 10s remain project goals; full-frame timing is
checkpoint-specific.
