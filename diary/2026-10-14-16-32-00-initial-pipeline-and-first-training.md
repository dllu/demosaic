# Initial pipeline and first training

Implemented the Python/PyTorch/uv project, linear-light 8×8 Commons ingestion,
attribution and source-hash splits, synthetic detail, geometry/optical/exposure
augmentation, electron Poisson/read-noise simulation, a 4.33M-parameter gated
multiscale network with coarse channel attention, optional frozen DINOv3 adapters,
reconstruction losses, resumable EMA training, evaluation, native Bayer RAW input,
16-bit TIFF output and streaming tiled inference.

The official DINOv3 HF source returns 403 for this token. The user confirmed that
access approval is pending and explicitly authorized other architectures and data
work meanwhile. No gated weights were obtained or random weights substituted.
Research includes August 2026 Structural Guidance for Unified JDD; see docs.

All 19 CPU tests pass, including physical noise moments, Bayer sampling, true
16-bit precision, odd-dimension tile phase, model gradients, checkpoint load and
bitwise restart equivalence of a four-step training experiment. Ruff passes.
CUDA 13 PyTorch 2.14.1 works on this GB10.

Bootstrap: 256 source records, 237 train / 13 validation / 6 untouched test.
1000 real-data training steps with 20% synthetic data completed. Validation EMA
at step 1000: 36.343 dB linear and 32.981 dB rendered, compared with 35.893/32.452
dB for noisy bilinear. This +0.53 dB rendered diagnostic is modest and nowhere
near proof of state-of-the-art or RawNIND superiority. Training used about 1.50 GB
peak CUDA allocation and 0.118 s/step including warmup/checkpoint overhead.

Actual 10000×10000 inference completed with finite RGB: 13.631 s for the tile
loop, 512 tiles / 64 overlap / batch 8, 529 tiles, 0.722 GB peak CUDA allocation.
It demonstrates 100 MP feasibility but misses the 10 s goal and excludes input
decode/output encoding. It overlapped the end of bootstrap training, so a clean
repeat is needed before profiling conclusions.

A personal GFX100S RAF was read without modifying the original: visible sensor
8746×11662, RGGB, per-channel black 62 and white 15872. Inspecting the resulting
preview conversion revealed an implausible green matrix row; LibRaw's `cam_xyz`
convention needs correction before any real-image preview is considered valid.
The main linear camera-RGB data path is independent of this preview matrix.

Artifacts remain local under `/mnt/external/demosaic`; generated images,
checkpoints, source paths and caches are not committed. Preparation of the first
1024 Commons sources is still running. Next: finish that set, correct/test color
conversion, run broader training, inspect held-out texture/highlight outputs,
profile tiled inference, and acquire comparison baselines. Full requirements
remain active in docs/requirements.md.
