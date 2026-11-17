# Review corpus coverage and larger full-model training

Recorded: 2026-11-17T00:04:23-08:00 (America/Los_Angeles).

Recorded a [larger-training and pipeline review](../docs/training-scale-pipeline-review-2026-11-17.md)
after the user challenged whether the corpus is underused. Corrected the scope
of the earlier inference: throughput saturation and a failed small-head 10×
continuation do not establish full-model training/data exhaustion.

Rechecked the existing source-schedule and epoch-order audits: the spatial20k
schedule draws112,424 photographic examples,56,256 from29 reviewed sources,
visiting42,086/90,781 source IDs. The optional5%-quota epoch sampler covers its
entire90,778-source cohort at20k. These are per-continuation source counts, not
the model's lifetime coverage, independent scene counts or trained-quality gains.

Inspected actual saved V120/V132 configs without model imports: both use strict
deterministic execution; V120 has2 workers per loader, V132 has0. The historical
policy benchmark has41.5% lower throughput under strict execution; no current
speedup is inferred. Reviewed source-cache cropping/augmentation, ordinary
transfers, batch fingerprints and the V131 wrapper's every-step input hashing.
Proposed profiling these costs and qualifying a new throughput-oriented policy,
with original frozen runs and receipts preserved.

The note proposes a full-model100k run with20k/50k/100k milestones, broader
sampling and fresh crop/noise coverage, with200k considered on useful curves.
It separates sampling, schedule/budget and whole-scene architecture comparisons.
It retains the other agent's active scene-context work, exact reference labels,
native image-review requirements and all protected-data exclusions.

Only this diary and the new note were authored. No training, profiling,
benchmarks, inference, GPU initialization, source-drive reads, process signalling
or changes to existing code/config/docs were performed. Local document links
and whitespace were checked; no implementation tests were needed.
