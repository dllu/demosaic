# Compile frozen DINO for faster Corpus 100k inference

Recorded: 2026-11-19T10:10:58-08:00 (America/Los_Angeles).

I compiled the four frozen ConvNeXt stages for the existing Corpus 100k EMA.
The engine uses FP16 convolutions with FP32 normalization, channel scaling
and residual additions. On GB10, resident DINO time drops from 31.96 to
20.69 ms. The combined trunk and DINO engine saves 17.19% versus eager FP16
in paired forwards over all 520 tiles. Pairing both TensorRT paths through
packing, transfer and blending gives 41.03 versus 39.35 s, a 4.10% reduction.
The two paired tile loops reproduce their respective complete TIFFs byte
for byte. Whole-restore wall times vary on the shared GPU.
[Timing and image comparisons](../docs/corpus100k-trt-dino.md) ·
[Machine results](../docs/results/corpus100k-trt-dino-v1/publication.json).

The fixed panel means move by at most 0.00024 dB versus the trunk-only
engine. The largest added photo loss is 0.02769 dB on the almost-white
GBRG sickle case. The RGGB case loses 0.2854 dB versus IEEE FP32, with
0.00261 dB added by DINO compilation. The native exact boards, full-export
outliers, and both standing GFX scenes were viewed. The sky is smooth
and the fine cab crossings remain incomplete. The weak-wire and true-gap
tests show very small paired differences. The supported CLI path uses
eager FP16. The targeted inference, RGB16, precision, and photo-order
tests give 54 passes.
[Native provenance](../docs/images/corpus100k-trt-dino-v1/manifest.json) ·
[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab mesh review](../docs/gfx-green-mesh.md).
