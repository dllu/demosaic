# Analyze completed CUDA inference and EMA measurements

Both queued controllers/final children exited successfully. Read the actual
operator traces with the existing positive-CUDA attribution reader. Every
inference activity maps through GPU external ID, unique runtime correlation
and same-thread CPU-launch containment:1093 no-DINO and1315 DINO activities.
Also mapped all four EMA traces:852/865 scalar kernels versus two grouped
kernels. No model inference or CUDA was run by this analysis.

The [execution report](../docs/mixed16-quarter-execution-profile.md) and
[receipt](../docs/results/mixed16-quarter-CUDA-execution-analysis-v1.json)
record source/checkpoint/trace hashes, strict producer-state receipts and
limits. The private/public result SHA256 is
`7d73cd68ec1393a7b74b4930f152f7368936a5fb512a5b29b196e144b18918b8`.
Private reader outputs remain in
`/mnt/external/demosaic/benchmarks/mixed16-quarter-CUDA-trace-analysis-v1/`.

Unhooked four512px-context medians are1120.038/1256.869ms. cuDNN convolutions
account for75.640/75.102% of traced GPU activity; six RAW groups dominate.
The DINO context has138.219ms inclusive activity,39.948ms inside the backbone
and98.271ms in remaining context work. Do not sum nested activity or equate
trace work totals with unhooked wall latency. Per-operator input shapes were
not recorded; no particular convolution shape is blamed without more evidence.

All80 EMA fixture updates pass producer byte/stride equality on actual10k
states. Isolated scalar/grouped synchronized medians are3.282/.400ms for
no-DINO and3.371/.393ms for DINO. This saves only2.882/2.978ms per update;
state traversal and whole-step timing remain excluded. No production adoption.

Next test inference cuDNN algorithm autotuning under the same IEEE FP32
policy, bounded memory/time and unchanged1DN16 max/.25DN16 RMS output gate.
The training source already enables cudnn.benchmark, so this cannot itself
be claimed as a new training speedup. No new quality run or training extension
has been launched. Complete states and prior evidence remain preserved.
