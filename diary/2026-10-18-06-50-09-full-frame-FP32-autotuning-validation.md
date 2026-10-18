# Full-frame FP32 autotuning passes numerical/export/native review

Four fresh serial processes completed on the cached101.996MP DSCF3879 RAW.
Same actual10k states, physical recipe, IEEE FP32,512/64/B4 and16GiB allocator
cap; opposite within-arm policy order. The original/autotuned full times are
159.525/62.648s for no-DINO and171.639/65.557s for DINO. Initial three actual
first-batch forwards are timed separately; first includes initialization/search,
without claiming a pure search measurement. No throughput-repeat confidence intervals.

The [report](../docs/mixed16-cudnn-fullframe.md) and
[complete registry](../docs/results/mixed16-cudnn-fullframe-v1.json) bind the
four cases, source/checkpoint hashes and complete audits. Private experiment:
`/mnt/external/demosaic/benchmarks/mixed16-cudnn-fullframe-v1/`.
Plan SHA256`0487afe0ee47ced4438be06ce720922bccacdda8be5b83edc37fc4f9030df6f3`;
publication SHA256`99616e3162fe9c2384e6450e1f487806031bd604ddeaebae4e2ccc48d236701b`.

Every611,975,112 unquantized RGB value passes the unchanged1DN16 max/.25DN16
RMS gate. Independent64-row/channel dot reductions/math.fsum reproduce
maximum exactly and RMS within1e−12 DN arithmetic agreement. Both global
maxima are.031249523DN16; RMS is.000379296/.000560062DN16. Complete model
state hashes also match the prior fixed-context profiles, including genuine
DINO; source/parameter identities, checkpoints and CPU/Python/CUDA RNG are unchanged.

Both candidate linear16 TIFFs are101.996MP uint16 RGB with matching metadata.
Every encoded value matches its saved F32 quantizer; sampled codes9,554/9,557
exceed8-bit cardinality. All four F32 arrays remain preserved. Actually viewed
all16 native triplets/24 cells at standing sky/building/foliage/fence ROIs.
No visible compute-policy change; the same grain and weak fine structure remain.
Fourteen8-bit preview channel values differ by one code. Separate ISO100 is
accurately not GT. Five published PNG copies preserve original pixels/metadata.

Quality and100MP/10s goals remain unmet. No production/default change or
training extension. Next test the stronger V43/V63 references. The first mature
probe failed before any forward because scripts/env.sh was sourced from a
frozen work directory, selecting its incomplete HF cache. Its source/plan/logs
and exited owners are preserved. The corrected v2 explicitly pins the existing
repository HF_HOME and both offline snapshot files; model, precision and16-bit
gates are unchanged. Its fresh serial probes subsequently completed; their
output-gate and native review remain separate from this full-frame result.
