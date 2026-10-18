# Bounded FP32 cuDNN autotuning probe

Explicit inference autotuning reduces observed four-context forward medians
from1120.04→422.35ms for V72 and1256.87→464.90ms for V73. Both pass the
original1DN16 maximum/.25DN16 RMS output gate. This is a promising engineering
result. The [subsequent full-frame comparison](mixed16-cudnn-fullframe.md)
now passes all output/export/native checks with observed159.53→62.65s and
171.64→65.56s restores. Production defaults remain unchanged while mature
references are tested.

[Frozen plan, worker/source/checkpoint/reference hashes, independent output audit and actual CUDA traces](results/mixed16-cudnn-autotune-v1.json).
The [completed quality report](packed-isotropic-mixed16-quarter-review.md)
keeps the same model weights unpromoted. No new training or quality score is added.

The [original traces](mixed16-quarter-execution-profile.md) attribute about75%
of GPU activity to cuDNN convolutions. Two serial bounded workers reuse that
exact frozen profiler and package, both actual10k checkpoints, the same four
512px GFX contexts, B4, channels-last and IEEE FP32 without AMP/TF32. Each
enables `cudnn.benchmark` with search limit10 under a16GiB CUDA allocator cap.
Initial subprocesses observe the previous benchmark flag as false. Existing
training already enables benchmarking, so this is an inference experiment.

| Arm | Original median ms | Autotuned median ms | Observed ratio | Maximum DN16 | RMS DN16 |
| --- | ---: | ---: | ---: | ---: | ---: |
| V72 no-DINO | 1120.038 | 422.348 | 2.652× | .011719 | .000320 |
| V73 DINO | 1256.869 | 464.897 | 2.704× | .015625 | .000577 |

Each run has three warmups, five unhooked synchronized samples, five hooked
samples and a separate trace. Timings exclude initial algorithm search,
checkpoint/input loading and output transfer. Original/candidate measurements
come from separate shared-machine processes, not balanced repeated throughput
trials. The observed ratios are not full-frame or training-speed results.

Every one of6,291,456 RGB values across both arms is compared with the saved
original FP32 output. Each complete context passes the original bounds;
independent float64 maximum errors agree exactly, and `math.fsum` RMS replay
agrees within1e−15 DN. The aggregate RMS values above do not replace per-context
acceptance. Floating-point outputs change within the recorded tiny bounds.
Repeated/hooked/traced outputs within each candidate are byte-identical; model,
actual DINO state, source files, checkpoints and CPU/CUDA RNG remain unchanged.

The new traces independently map all1009/1217 positive GPU activities.
The quarter-stem activity falls from124.314→3.006ms for no-DINO and
122.360→3.418ms for DINO. Six RAW-group activity totals fall from941.241→
369.248ms and951.743→365.617ms. The remaining DINO context activity is
5.157ms, with40.656ms inside its separately counted backbone. These are
exclusive instrumented activity sums, distinct from elapsed wall latency.

Post-warmup peak CUDA allocations are.421/.567GB, versus7.042/7.189GB in
the original profiler. Those figures exclude initial search and do not measure
total unified RAM or cached/reserved allocator memory. Both workers exited
successfully within their300-second limits; launch required48GiB available
RAM and500GiB free SSD space. Original sources and prior outputs remain intact.

Production defaults are unchanged. Complete serial original/autotuned FP32
restores have now passed full-output1DN16 max/.25DN16 RMS checks, with
initial forwards timed separately from restoration/blending. The original
failed FP16 result and its strict precision gate remain preserved.
