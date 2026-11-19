# Fixed camera panels for scene 50k and the paired continuation

The completed measured-CFA panels show a known-camera cost for both
50k models. Spatial 50k loses **0.12252 dB** on known cameras and
gains **0.00638 dB** on unseen cameras versus Corpus 100k. The signed
paired continuation improves on its absolute-loss control by
**0.04198 dB known and 0.07490 dB unseen**. Its known-camera result
remains below the local-only parent and V120.

[Machine results](results/scene-050000-camera-v1/publication.json) ·
[Per-batch evidence](results/scene-050000-camera-v1/evidence.tar.xz) ·
[PSNR history](performance-history.md).

## Fixed camera scores

All endpoints use EMA with CUDA IEEE FP32. The four known-camera
scenes contribute eight capture pairs and 72 native crops. The five
unseen-camera scenes contribute ten pairs and 90 native crops. The
evaluation uses the frozen measured-CFA masks, sensor levels and
scoring borders. Each reported mean first averages the crops within
each pair, then balances the pairs and scenes. The replay's V120
means differ from the archived V120 by +0.00000149 dB known and
+0.00000117 dB unseen. The audit verifies the canonical inputs for
all 54 batches and archives their per-crop scores and output hashes.

| EMA | Known CFA PSNR | Unseen CFA PSNR |
| --- | ---: | ---: |
| V120 | 54.31272 dB | 54.00872 dB |
| Corpus 100k | 54.33708 dB | 53.97826 dB |
| Local-only 50k | 54.22726 dB | 53.97844 dB |
| Spatial 50k | 54.21456 dB | 53.98465 dB |
| Absolute continuation, +512 steps | 54.13283 dB | 53.95658 dB |
| Paired continuation, +512 steps | 54.17481 dB | 54.03148 dB |

Relative to local-only 50k, spatial context changes known CFA by
−0.01270 dB and unseen CFA by +0.00620 dB. Relative to local-only 50k,
the paired continuation changes known by −0.05244 dB and unseen by
+0.05304 dB. Paired training gains the most over its absolute-loss
control on the unseen *Coulicoco* scene, by about 0.200 dB.
All four new checkpoints' fixed 427-photo evaluations are running.

The companion reports give the checkpoint hashes, training budgets,
native exact-target triplets and both standing GFX comparisons.
[Matched 50k native review](scene-50000-native.md) ·
[Paired continuation report](local-paired-continuation.md). Those GFX100S captures are a
separate qualitative set with independent ISO100 and JPEG references.
This report contributes only the fixed known/unseen measured-CFA
scores to the chart. The full427 results remain pending.
