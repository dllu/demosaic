# Matched10k CUDA execution measurements

The completed IEEE FP32 profiles identify cuDNN convolutions as the main
inference cost. Grouped EMA passes exact-state CUDA checks and reduces isolated
update latency, but saves only about3ms per update. Neither measurement changes
production code or establishes a whole-step training speedup.

[Source/checkpoint/trace hashes, exact exited owners and numerical results](results/mixed16-quarter-CUDA-execution-analysis-v1.json).
The [complete quality review](packed-isotropic-mixed16-quarter-review.md)
keeps both models unpromoted. These engineering measurements add no quality score.

## Inference

Each actual10k EMA checkpoint uses the same four512px GFX contexts, B4,
channels-last and IEEE FP32 without AMP/TF32. Three warmups precede five
unhooked synchronized samples, five hooked samples and one operator trace.
All repeated/hooked/traced outputs are bitwise equal within each arm; model,
actual DINO state, checkpoint bytes and CPU/CUDA RNG stay unchanged.

| Measurement | V72 no-DINO | V73 DINO |
| --- | ---: | ---: |
| Unhooked forward median, ms | 1120.038 | 1256.869 |
| Traced GPU activity sum, ms | 1125.518 | 1276.878 |
| cuDNN convolution activity, ms | 851.343 | 958.964 |
| cuDNN share of activity | 75.640% | 75.102% |
| Six RAW groups, exclusive activity, ms | 941.241 | 951.743 |
| Mapped positive GPU activities | 1093 | 1315 |

The DINO context adds138.219ms of inclusive traced activity, including39.948ms
inside its backbone. The remaining context projection/fusion accounts for
98.271ms. The RAW quarter stem costs124.314/122.360ms. GPU activity sums are
instrumented work totals, not elapsed latency. Exclusive ranges avoid counting
the backbone twice or adding a parent RAW range to its children.

The reader independently cross-checks every GPU external ID against its CPU
operator, unique CUDA runtime correlation and same-thread launch containment.
No GPU event is unmapped. CPU operator counts alone do not establish this
attribution. The source trace did not record per-operator input shapes; module
hook shapes and named ranges are retained separately.

The inference profiler does not enable cuDNN algorithm benchmarking; training
already enables it. The [subsequent bounded autotuning probe](mixed16-cudnn-autotune.md)
passes the existing1DN16 max/.25DN16 RMS output gate, with observed medians
of422.348/464.897ms. The [full-frame validation](mixed16-cudnn-fullframe.md)
also passes; mature-reference testing precedes any default change.
This is an inference experiment; it cannot be presented as a new training optimization.

## EMA

The GPU producer checks all852/865 actual FP32 restoration-state tensors,
including DINO preprocessing buffers, at eight schedule positions with five
updates each. Every update is byte-identical to the original scalar loop with
matching strides. Source/initial EMA, checkpoint bytes and CPU/Python/CUDA RNG
stay unchanged. This reader checks those receipts and hashes; it does not
repeat tensor arithmetic.

Three warmups and ten balanced shuffled synchronized samples per method give:

| Method | V72 wall median, ms | V73 wall median, ms |
| --- | ---: | ---: |
| Original scalar EMA | 3.282 | 3.371 |
| Grouped `_foreach_lerp_` | .400 | .393 |

Separate traces map852/865 scalar kernels versus two grouped kernels. Their
summed device activities are1.270/1.282ms versus.154/.167ms; those trace sums
are distinct from synchronized wall samples. The isolated loop is roughly8×
faster, saving2.882/2.978ms. It excludes real-model `state_dict` traversal,
network, data and optimizer work. A whole-step measurement remains necessary
before adoption; the production scalar loop is unchanged. These small absolute
savings do not explain the large full-frame inference cost.

Both original controllers and final children exited successfully. All results
are shared-machine observations; five inference samples or ten EMA samples
are not repeat-run confidence intervals or an idle hardware optimum.
