# Documentation guide

Start with the [README](../README.md) for setup and full-frame inference,
[current model choices](current-model.md) for measured strengths and limits,
and [architecture](architecture.md) for the consolidated code and experiment
workflow. V120 Small remains the general recommendation.

| Task | Documentation |
| --- | --- |
| Run inference or export DNG/JPEG | [Usage](usage.md), [DNG export](dng-export.md) |
| Start or resume a configured experiment | [Current experiments](experiments.md), [architecture](architecture.md) |
| Understand broad training data | [Training pipeline](training-pipeline.md), [current source review](current-source-loss-review.md) |
| Evaluate restoration quality | [Evaluation](evaluation.md), [V120 results](v120-v121-primary.md) |
| Inspect latest detail/quiet tradeoffs | [Shared-edge](shared-edge-comparison.md), [three-noise finite wires](edge-snr-ladder.md), [V200](scale-supported-cfa-wave-comparison.md) |
| Follow the new carrier-allocation trial | [Proposal](competing-wave-candidates.md), [native review](competing-orientation-comparison.md), [conditional response](competing-edge-response.md): weak-direction gains with strong-direction losses |
| Follow the full-model comparison | [V131 completed control quality](v131-endpoint-quality.md); [V132 matched1k review](v132-progress1000-quality.md): small faint gain versus V1311k, still below V120. [Production](raw-spatial-continuation.md) training, [endpoint review](raw-spatial-endpoint-review.md) follows |
| Inspect the remaining weak-response limit | [Coverage/response diagnostic](complementary-coverage-quality.md); [fixed-wave GT oracle](measured-wave-oracle.md): more response, persistent quiet/increment costs |
| Follow input-derived localization | [Local conditional wave prototype](local-validated-waves.md): pilot improves global-support tradeoff; full three-prior comparison running |
| Inspect waveform capacity and its cost | [Matching and harmonic follow-up](local-wave-shapes.md): more response, higher increment error and building bands; assignment fix retained |
| Follow the added-stage trial | [Complementary CFA branch](complementary-comparison.md): full review finds almost unchanged weak detail and slightly higher quiet/flat error; [fresh-noise follow-up](complementary-edge-response.md) retains a small lower-noise gain |
| Review literature and next weak-detail ideas | [November 2026 review](weak-detail-literature-2026-11.md), [withheld CFA](withheld-cfa-evidence.md), [edge refinement](withheld-cfa-edge-refinement.md) |
| Inspect real-camera weaknesses | [Main GFX scene](gfx-qualitative.md), [fine green mesh](gfx-green-mesh.md), [other cameras](cross-camera-qualitative.md) |
| Manage cached artifacts | [Storage](storage.md) |
| Understand historical decisions | [Diary](../diary/index.md), [experiment archive](history/experiments-through-v200.md) |

The pre-consolidation [model catalogue](history/current-model-through-v200.md),
[documentation guide](history/index-through-v200.md) and
[experiment index](history/experiments-through-v200.md) preserve all earlier
links and measured implementations. Running/queued descriptions in those
snapshots record their original writing context rather than current job state.
Machine receipts, frozen sources, checkpoint identities and historical artifact
paths are retained.
