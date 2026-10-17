# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with 16-bit TIFF
output, physical noise conditioning, tiled inference, and an optional DINOv3
feature branch. Experimental: training and quality validation are in progress.
The [latest native-data review](docs/native-corpus-2k-review.md) finds a
0.09 dB gain on 427 synthetic-noise photos versus the matched control at step 2000.
The [augmentation change](docs/geometry-corpus-v34-v36-review.md) previously
gained 0.51 dB. Low-noise pattern regression, real-camera tradeoffs and fine-detail
deficits remain.
Quality work continues;
state-of-the-art performance is not established.
The [completed 10,000-step fresh DINO comparison](docs/fresh-dino-capacity-10k-review.md)
improves average synthetic-photo scores but finds no consistent DINO advantage;
fabric color shifts and lost fine texture keep V43 as the working reference below.
The [completed ConvNeXt pyramid review](docs/dino-convnext-pyramid-v58-10k-review.md)
ties that photo mean and retains color/detail limitations.
The [released RAW reference comparison](docs/nonlocal-reference-full-review.md)
adds a recent comparator with mixed real/synthetic results.
The [completed 4,000-update palette review](docs/wide-flat-palette-full4k-review.md)
finds small photo gains and better highly saturated colors; bright-color errors,
fine-detail loss and paired-real tradeoffs still prevent promotion.
The [expanded-data comparison](docs/long-commons-v63-v64-first4k-review.md)
finds a small mixed effect at 4,000 updates; native crops still show soft detail.
The [joint RAW-kernel review at2k](docs/raw-kernel-phase-joint-v67-first2k-review.md)
improves denoising over its initializer but still trails mature V60; it is not promoted.

Native 160×160 validation crops: noisy → denoised → GT, using V43 step 2000
(FP16, ISO12800 synthetic noise prior). These are 100% crops at the 8×8-binned
evaluation resolution, with identical display transforms; open the PNG at 100%.
They illustrate current behavior, including lost fine detail.

![Noisy, denoised and GT: fabric detail](docs/images/native-2k-v43-full427-0014aa4e.png)

![Noisy, denoised and GT: building and sky](docs/images/native-2k-v43-full427-002fc6ee.png)

Sources: [Roy Egloff](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg)
and [Dietmar Rabich](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); modified by binning,
cropping, simulated noise and restoration. See [the performance review and crop receipts](docs/native-corpus-2k-review.md)
and [real GFX100S crops](docs/gfx-qualitative.md).

Real GFX100S foliage and chain-link-fence crops at native 160×160 sensor resolution:
DSCF3879 noisy ISO6400 → experimental V43 step 2000 → DSCF3880 ISO100 f/5.6,
with shared +2 EV display, cropped from the full 102 MP output.
This closer pair is now the standing test. Framing is nearly identical, 3m38s
apart; aperture and moving subjects differ, so the last panel is a qualitative
reference, **not GT**. [All four regions and matched comparisons](docs/native-corpus-2k-review.md).
Additional [Q2, a7R II and GFX50R native comparisons](docs/cross-camera-qualitative.md)
use locally cached captures and explicitly labeled RawNIND comparators.

![GFX foliage: noisy, denoised and separate low-ISO reference](docs/images/native-2k-v43-gfx-full-foliage.png)

![GFX fence: noisy, denoised and separate low-ISO reference](docs/images/native-2k-v43-gfx-full-chain-link-fence.png)

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic prepare --output /mnt/external/demosaic/commons-v1 --limit 1024
uv run demosaic train configs/base.yaml
uv run demosaic evaluate /mnt/external/demosaic/runs/base-v3/best.pt \
  --manifest /mnt/external/demosaic/commons-v1/manifest.jsonl \
  --output /mnt/external/demosaic/evaluation/base-v3.json
uv run demosaic infer /mnt/external/demosaic/models/v43-step2000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --precision float16
uv run pytest -q
```

Noise values above are examples, not measured camera profiles. Setup requires
Linux, Python 3.12+, uv, and a CUDA 13-compatible NVIDIA driver for this lockfile.
DINOv3 additionally requires approved Hugging Face access via `HF_TOKEN`.
See [experiment results](docs/experiments.md), [quality and noise diagnostics](docs/evaluation.md),
[usage and data conventions](docs/usage.md), [research](docs/research.md),
and the [completion evidence checklist](docs/requirements.md).
The [Commons archive download](docs/commons-download.md) is running separately;
active experiments retain frozen manifests.
See [training pipeline work](docs/training-pipeline.md) for augmentation before
the last reduction, selected-domain loading and the batch-size sweep.
The [packed detail review](docs/packed-detail-v40-v41-review.md) retains the
full-resolution model after testing two native-detail variants.
See the [V37 inference precision and timing review](docs/hidden-autocast-v42-review.md)
for an opt-in export with unchanged learned weights.
