# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 features and tiled16-bit output on NVIDIA GB10.
**V114 Tiny is the current general quality baseline**, using V84's pretrained
DRUNet RGB trunk and official DINOv3 ConvNeXt-Tiny pyramid. It reaches
**36.980dB** on the full427-photo panel, +.077dB over V112, with422/427 source
means improving. Known/unseen measured-CFA means are54.286/54.003dB.
[Complete results, native comparisons and remaining weaknesses](docs/v114-v115-quality.md).

**V115 Small is a useful alternative:** its known-camera mean is higher at
54.324dB and its tested eight-pixel weak-carrier response improves. Tiny has
slightly higher photo PSNR and lower tested color bias. Both retain soft fine
foliage/neon detail and dark-camera mottling. All numerical panels, independent
saved-prediction checks, native review and complete102MP RGB16 exports are done.
[Current choices](docs/current-model.md) · [GFX gallery](docs/gfx-qualitative.md).

[V116 is training](docs/fine-detail-data-training.md) to test fine weak sources
and reviewed paired-reference masks against the matched V114 control. Its
quality is pending. The90,864-source corpus, zero optical blur and geometry
before final downsampling remain in use. [Data review](docs/incoming-commons-quality.md) ·
[Training pipeline](docs/training-pipeline.md) · [Historical diary](diary/index.md).

Earlier useful modes remain available: [V104 eight views](docs/dihedral-quality.md)
reaches37.044dB on the full photo panel, with a worse ADC color tail;
[V112 eight views](docs/v112-eight-view.md) improves twelve fixed material cases
but has no complete-panel/frame measurement. V114 eight-view quality is
unmeasured. The [V104 ADC sites option](docs/adc-consistency.md) and
[camera-outlier study](docs/camera-outliers.md) retain their explicit weights
and measured tradeoffs.

![PSNR versus model version](docs/images/version-PSNR-history.png)

[PSNR history and full values](docs/performance-history.md). Versions have unequal
training budgets and data; this describes available models rather than an
isolated architecture ablation.

## Current100% crops

Noisy observation → **V114 Tiny** → exact synthetic GT, ISO12800 prior.
Each cell is an unchanged160×160 crop at the8×-binned evaluation resolution,
with shared coordinates and display transforms. Fine texture remains softer
than GT. [Tiny/Small comparison](docs/v114-v115-quality.md) ·
[Source/ROI/checkpoint/noise/display receipts](docs/images/v114-v115-quality/manifest.json).

![V114 bark: noisy, restored and exact GT](docs/images/v114-v115-quality/V114-material-1.png)

![V114 canopy: noisy, restored and exact GT](docs/images/v114-v115-quality/V114-material-2.png)

Sources: [Derek Ramsey](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA2.5](https://creativecommons.org/licenses/by-sa/2.5/), and
[Grendelkhan](https://commons.wikimedia.org/wiki/File:Forest_covered_hills_on_Yakushima.jpg),
[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by binning,
cropping, simulated noise and restoration.

Real GFX100S: DSCF3879 ISO6400 → **V114 Tiny** → DSCF3880 ISO100 f/5.6.
Native160×160 sensor-pixel crops from complete102MP outputs share +2EV display.
The independent ISO100 exposure is an approximate qualitative reference,
**not GT**. Fine foliage remains painterly; fence geometry is coherent.
[All six Tiny/Small regions and other useful models](docs/gfx-qualitative.md) ·
[Metadata](docs/images/v114-v115-quality/manifest.json).

![V114 GFX foliage: noisy, restored and separate ISO100 reference](docs/images/v114-v115-quality/V114-foliage.png)

![V114 GFX fence: noisy, restored and separate ISO100 reference](docs/images/v114-v115-quality/V114-chain-link-fence.png)

The [stronger RawNIND full-frame reference](docs/rawnind-fullframe.md) and
[Q2/Sony/GFX50R comparisons](docs/cross-camera-qualitative.md) retain additional
real-camera limitations. Broad real-photo superiority remains a goal.

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v114-final20000.pt photo.raf \
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
