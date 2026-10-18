# Bounded FP32 inference autotuning passes the original output gate

After confirming all exact prior GPU owners/children had exited, ran two
serial bounded cuDNN autotuning probes through the unchanged frozen profiler
and package. The plan limits each child to300s, the CUDA allocator to16GiB,
and requires48GiB available RAM/500GiB free SSD space. The comparison helper
was copied unchanged into the new private experiment, with its source hash
pinned before execution. No existing source, checkpoint or output was modified.

Both actual10k arms pass per-context1DN16 max/.25DN16 RMS limits over all
four512px GFX RGB outputs. Independent float64 maximum/math.fsum RMS checks
replay all6,291,456 values. Largest differences are.011719/.015625DN16.
No tolerance was relaxed. Within each candidate, repeated/hooked/traced outputs
are bitwise equal and model/DINO/RNG/checkpoint identity checks pass.

Original/autotuned unhooked medians are1120.038/422.348ms for no-DINO and
1256.869/464.897ms for DINO: observed2.652×/2.704× ratios in separate shared
processes. Actual worker3272972/1792329607.25 and3273279/1792329645.64
both exited successfully. New positive GPU activities1009/1217 all map through
external IDs, unique runtime correlations and CPU-thread launch containment.
Quarter-stem and RAW-group cuDNN costs fall substantially in the actual traces.

The [report](../docs/mixed16-cudnn-autotune.md) and
[independent output/trace receipt](../docs/results/mixed16-cudnn-autotune-v1.json)
record the complete results and limits. Private root:
`/mnt/external/demosaic/benchmarks/mixed16-cudnn-autotune-v1/`.
Plan SHA256`219c98e7ad3b64a9173674b6aa99499c1addf80d3beef7dba3936b97560e1918`;
audit SHA256`dbfe4edb02f4247d9bdb85ad47229eed26c5d943f03b94265979cf8b96b5356c`.

No production adoption, training extension or quality promotion. Initial
autotuning search is excluded from these medians. Training already enables
cudnn.benchmark, so these ratios cannot be claimed as training gains. Next
validate complete serial original/autotuned FP32 restores, all output pixels
against the unchanged16-bit gate, and separate initial-search timing from
steady restoration/blending. The original full-frame speed target and quality
goal remain unmet; V43 stays the README working reference.
