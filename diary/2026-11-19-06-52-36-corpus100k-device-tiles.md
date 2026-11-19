# Corpus 100k FP16 tile transport

Recorded: 2026-11-19T06:52:36-08:00 (America/Los_Angeles).

The supported Corpus 100k FP16 path uses 512-pixel tiles, overlap 64
and batches of four. Seven restores of cached DSCF3879 produce the same
RGB16 TIFF byte for byte. Three ordinary passes take 39.60–40.60 s.
Device-resident blending, caching the fixed Bayer kernels and replaying
the full neural forward in a CUDA Graph take 39.97–41.01 s. Device-resident
passes raise peak PyTorch CUDA allocation from 2.12 GB to 4.18–4.21 GB.
CPU blending accounts for 0.82–1.29 s in the ordinary passes.

Fresh-process cuDNN FP16 search reduces the resident B4 median from
298/331 ms to 276 ms and lengthens the first forward to 10.48 s. It changes
the native result by 0.201 DN16 RMS. The tested transport and replay
variants reproduce the ordinary FP16 values across six exact-target
contexts and eight viewed standing GFX crops. The smooth sky and coarse
crossings persist. Building and foliage detail stay soft, and close cab
crossings are incomplete. Production inference continues to use standard
FP16. The existing TensorRT FP16 pilot remains the measured faster option
with small average quality changes and a larger individual highlight loss.

[Full timings and two exact-target triplets](../docs/corpus100k-device-tiles.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md) ·
[Prior fixed panels](../docs/corpus100k-fp16-throughput.md#tensorrt-fp16-on-the-fixed-panels).
