# Fixed photo and camera panels for scene 50k and the paired continuation

Local 50k reaches **37.27953 dB** on the fixed 427-photo panel,
**+0.03205 dB** over Corpus 100k. Spatial 50k is within 0.001 dB of
Local 50k. The paired continuation improves both camera means over
its absolute-loss control and loses **0.00852 dB** on the photo panel.

The completed measured-CFA panels show a known-camera cost for both
50k models. Spatial 50k loses **0.12252 dB** on known cameras and
gains **0.00638 dB** on unseen cameras versus Corpus 100k. The signed
paired continuation improves on its absolute-loss control by
**0.04198 dB known and 0.07490 dB unseen**. Its known-camera result
remains below the local-only parent and V120.

[Machine results](results/scene-050000-camera-v1/publication.json) ·
[Per-batch evidence](results/scene-050000-camera-v1/evidence.tar.xz) ·
[PSNR history](performance-history.md).

## Fixed 427-photo scores

The compact replay uses identical Bayer inputs for 427 photos,
seven noise and exposure conditions, and four CFA patterns. Each
checkpoint contributes 11,956 scored photo observations. The mean
balances conditions and CFAs within each photo, then balances the
photos. The same plan, checkpoint hashes and CUDA IEEE FP32 EMA
policy bind both the photo and already published camera panels.
Photo and camera metrics use their respective reference targets.

| EMA | Source-balanced sRGB PSNR | Δ vs Corpus 100k |
| --- | ---: | ---: |
| V120 | 37.04008 dB | −0.20739 dB |
| Corpus 100k | 37.24747 dB | — |
| Local-only 50k | 37.27953 dB | +0.03205 dB |
| Spatial 50k | 37.27886 dB | +0.03139 dB |
| Absolute continuation, +512 steps | 37.25435 dB | +0.00688 dB |
| Paired continuation, +512 steps | 37.24583 dB | −0.00164 dB |

The source-paired 95% interval for Local 50k versus Corpus 100k
is **+0.02181 to +0.04131 dB**. Spatial minus Local is **−0.00067 dB**
[−0.00251, +0.00109]. Both 50k arms gain around 0.049 dB at ISO100
and 0.032 dB at ISO12800 versus Corpus 100k. Their highlight means
are within 0.003 dB of Corpus 100k. The paired continuation loses
0.00852 dB [−0.00988, −0.00721] against absolute loss and 0.03369 dB
[−0.03811, −0.02992] against its Local 50k parent. Its largest loss
against Local 50k is in highlights, at 0.08497 dB.

The full replay reproduces the previously archived camera means.
The [photo machine summary](results/scene-050000-primary-v1/publication.json)
and [per-batch audit](results/scene-050000-primary-v1/evidence.tar.xz)
bind the 3,108 exact photo batches, both camera batch counts, the
checkpoint identities and the retained V120 CPU qualification.

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
The companion reports give the checkpoint hashes, training budgets,
native exact-target triplets and both standing GFX comparisons.
[Matched 50k native review](scene-50000-native.md) ·
[Paired continuation report](local-paired-continuation.md). Those GFX100S captures are a
separate qualitative set with independent ISO100 and JPEG references.
