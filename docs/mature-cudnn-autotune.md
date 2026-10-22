# Mature V43/V63 FP32 autotuning probes

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

V43/V63 pass the original16-bit output limits with observed four-context median
ratios of1.60×/1.64×. Their native views show no visible compute-policy change.
These are context probes; complete-frame validation remains required before
changing inference defaults.

[Complete source/checkpoint/backbone hashes, numerical gate, CUDA traces and native-view receipt](results/mature-cudnn-autotune-v2.json).
[Full-frame validation of the experimental10k pair](mixed16-cudnn-fullframe.md) and
[existing quality comparisons and exact-GT photo board](packed-isotropic-mixed16-quarter-review.md).
No new training or model-quality score is added here.

| Model | Original median ms | Autotuned median ms | Observed ratio | Maximum DN16 | Worst context RMS DN16 |
| --- | ---: | ---: | ---: | ---: | ---: |
| V43 step2000 | 1481.427 | 926.416 | 1.599× | .058593 | .000994 |
| V63 step20000 | 1416.573 | 865.949 | 1.636× | .062499 | .000916 |

Four fresh serial processes use the actual mature EMA checkpoints, four fixed
512px GFX contexts, B4, channels-last and IEEE FP32 without AMP/TF32 or hidden
autocast. Each has a16GiB allocator cap, three separately timed warmups, five
unhooked synchronized samples and one separate trace. The first warmup includes
initialization/search; sample medians exclude it. Policy order is reversed
between the two models. These separate shared-machine observations are not
balanced repeat-run confidence intervals, full-frame or training speeds.

All6,291,456 unquantized RGB values pass **1DN16 maximum/.25DN16 RMS** per
context, with no clipping/resizing/correction. Independent float64 maximum
and`math.fsum` RMS checks agree with the original comparison helper within
1e−15 DN arithmetic error. Maximum errors above are across all four contexts;
the last column reports the worst per-context RMS rather than an aggregate.
No original limit is relaxed.

Model states, actual DINO backbones, checkpoints and CPU/Python/CUDA RNG remain
unchanged. All repeated/traced outputs within each case pass byte equality,
including signed-zero representations. CUDA trace association verifies all
1,611/1,111 original/autotuned V43 activities and1,485/963 V63 activities
through external IDs, runtime correlation and thread containment.

The [native board](images/mature-cudnn-autotune-native.png) contains all16
triplets/24 unresized160px cells at the standing sky, building, foliage and
chain-link-fence coordinates. All were actually viewed at original resolution.
Original/autotuned pairs have no visible difference. Both mature models have
clean sky/building and continuous fence structure; foliage remains soft.
These are512px context outputs rather than full restores. Noisy and independent
ISO100 panels share the same inputs, WB/matrix and display exposure4(+2EV)
across all methods. The ISO100 f/5.6 capture is a qualitative reference, **not GT**.
Source/ROI/checkpoint/noise/display settings are retained in the registry.

The first attempt stopped in V43 construction before any forward because
`scripts/env.sh` was sourced from the frozen working directory and selected
its incomplete HF cache. That failed source/plan/log/status remain preserved.
The corrected experiment sources the environment from the repository and
explicitly pins the existing offline ViT-S/16 and ConvNeXt-tiny snapshots.
No model, input, precision or numerical gate changed; no download was needed.

All four workers and their controller exited successfully. Production defaults
remain unchanged, and V43 was the reference for this experiment. Next validate
complete V43/V63 original/autotuned outputs and RGB16 exports with the same
strict gate and adequate reserved disk space. The100MP/10s and SOTA objectives
remain unmet/unproven.
