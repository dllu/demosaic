# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with 16-bit TIFF
output, physical noise conditioning, tiled inference, and an optional DINOv3
feature branch. Experimental: training and quality validation are in progress.
No state-of-the-art or RawNIND superiority claim has been established.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic prepare --output /mnt/external/demosaic/commons-v1 --limit 1024
uv run demosaic train configs/base.yaml
uv run demosaic evaluate /mnt/external/demosaic/runs/base-v3/best.pt \
  --manifest /mnt/external/demosaic/commons-v1/manifest.jsonl \
  --output /mnt/external/demosaic/evaluation/base-v3.json
uv run demosaic infer /mnt/external/demosaic/runs/base-v3/best.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff --shot 0.001 --read 0.000001
uv run pytest -q
```

Noise values above are examples, not measured camera profiles. Setup requires
Linux, Python 3.12+, uv, and a CUDA 13-compatible NVIDIA driver for this lockfile.
DINOv3 additionally requires approved Hugging Face access via `HF_TOKEN`.
See [experiment results](docs/experiments.md), [usage and data conventions](docs/usage.md), [research](docs/research.md),
and the [completion evidence checklist](docs/requirements.md).
