# IEEE FP32 CUDA replay of closed local-model batches

CUDA reproduced all 24 probed CPU outputs within the existing pixel bounds.
The maximum difference was **0.249996 DN16** and the largest per-output RMS
was **0.022297 DN16**, just inside the respective limits of 0.25 and 0.025.
The largest primary score change was **0.00000448 dB**. Both the V120 and
Corpus20k EMA checkpoints used identical retained benchmark inputs.
[Probe and independent audit](results/local-primary-cuda-probe-v1/publication.json).

The probe covers eight photo batches across all seven noise and exposure
conditions and four CFA layouts. It also covers two known and two unseen camera
batches, with both four-crop and one-crop batches. The photo slice includes two
highlight batches. The previous V120 scene-benchmark probe exceeded the pixel
limits on highlights, so the small margin here matters. Batch selection,
checkpoint and physical-input hashes, and per-output differences accompany
the receipt. [Previous CPU qualification](whole-scene-context-primary-admission.md).

| Slice | Batches per model | CPU forward sum (s) | CUDA forward sum (s) |
| --- | ---: | ---: | ---: |
| Photos | 8 | 164.647 | 24.301 |
| Known camera | 2 | 107.000 | 6.564 |
| Unseen camera | 2 | 106.250 | 5.804 |
| Total | 12 | 377.897 | 36.670 |

CUDA uses channels-last IEEE FP32, with autocast and cuDNN autotuning disabled.
Each checkpoint makes its own DINO calls. The CPU receipts include the
existing shared-feature replay. These are sums of forward times recorded in
different sessions with concurrent training and evaluation. CUDA forward
timing synchronizes before and after each call. The probe took 44.864 seconds
after loading and used 3.255 GiB peak allocated and 3.752 GiB peak reserved
under a 4 GiB process cap. Model startup, observation transfer, metric
computation and full-frame RAW export have separate costs.

An independent NumPy reduction checks all 24 pairs and recomputes photo sRGB
and camera measured-CFA score deltas with the original borders. The probe
reuses previously decoded inputs and performs zero optimizer updates or
sensor draws. The existing full CPU collections continue under their original
protocol. A future CUDA comparison can apply one policy to both fresh arms,
with checkpoint-specific and highlight checks extended before a broad run.
