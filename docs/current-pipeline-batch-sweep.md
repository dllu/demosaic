# Current 4× augmentation/native128 batch sweep

Batch16 remains the controlled quality-trial setting: **30.81
native256px training patches/s**, 12.1% above batch4. Batch32's mean is
1.3% higher with roughly twice the CUDA allocation. Batch64 adds no clear
throughput benefit. These are two repeats on a shared machine, not confidence
intervals or a unique hardware optimum.
[Complete measurements and runtime-config verification](results/training-batch-sweep-v2.json).

| Batch | Mean patches/s | Two-run range | Peak CUDA GB |
| ---: | ---: | ---: | ---: |
| 4 | 27.47 | 27.37–27.57 | 2.23 |
| 8 | 29.65 | 29.53–29.77 | 3.73 |
| 16 | 30.81 | 30.71–30.91 | 6.95 |
| 32 | 31.21 | 31.17–31.26 | 13.41 |
| 64 | 30.76 | 30.40–31.13 | 26.33 |

This repeats the [earlier sweep](training-pipeline.md#batch-size-sweep) on the
actual complete4× Commons/native128 path: geometry/PSF at twice target resolution,
then final area2. The frozen V43 first1000 EMA, pinned DINOv3, full-resolution RGB
CNN, original precision, seed47, data proportions, manifests, LR and worker
counts remain fixed. Only batch size varies. All ten runtime configs verify the
same initializer and source bundle `bd08aed2689112a6cb3319c20da81577a62de23fe550dc00a355bd17f8012efc`.
No low-rank DINO adapters or V42 hidden-autocast policy are enabled.

The deterministic shuffled order repeats batches4/8/16/32/64 twice. Each fresh
process excludes15 warmup updates and measures45. Every case has24 Commons/
procedural,11 paired and10 native updates in that measurement window. Timing
includes selected-domain I/O/augmentation, physical noise/GAT work, DINO,
forward/backward, AdamW and EMA. It excludes startup, warmup, validation and
checkpoint serialization. The benchmark uses a common planned5000 schedule;
its60-update runs are not quality trials. Larger batches process more examples
per update, so this does not establish an equal-image convergence gain.

Peak CUDA allocation is not total unified system RAM. Every launch verifies
memory headroom. The sweep began only after the owned V37/V39/V43 training,
full427 review and full102MP GFX evaluation completed and the controller exited.
The adapter GPU checks wait for this sweep's process exit. Other users' work
remains untouched; the measured ranges include shared-machine variation.

Keep batch16 in the prepared controlled recipes. A future batch32 quality trial
must be reviewed on its own merits before changing those comparisons. The
[step2000 corpus review](native-corpus-2k-review.md) is separate quality evidence,
including its low-noise procedural regression. This benchmark does not repair
that failure or establish better restoration quality.
