# Experiment status and workflow

Reviewed November 17, 2026. This page tracks research outcomes and the next
questions. Use the [model guide](current-model.md) to choose an implementation;
individual reports retain exact measurements, native comparisons and receipts.

## Active and unresolved work

| Work | Evidence available | Next unresolved question |
| --- | --- | --- |
| [Whole-scene context](whole-scene-context-development64.md) | All3 matched2k arms,64-source/intervention analysis and24 final native boards complete, including both GFX families. Spatial has small quiet-coarse gains with detail/color costs; no convincing new crossings.55 focused tests pass | [Full427/known-unseen evaluation running on CPU](whole-scene-context-primary-admission.md), exact canonical inputs and matched CPU V120. V120/V131 remain the last completed broad evaluations |
| [A-only parent-innovation validation](parent-innovation-validation.md) | Both 48-case numerical reviews complete with zero new neural calls | Native viewing and the quality decision are still pending in the published report |
| [Full-corpus scaling](full-corpus-scaling.md) |First1000 of100k updates complete:5045 photo IDs/5294 visits.90778-photo epochs,5% reviewed quota, native/paired retained; fresh20k control running after all3 completed context probes, then remaining99k. B16 warm throughput24.96 patches/s versus14.82 strict |20/50/100k learning curves, full427/known-unseen camera panels and both fence reviews. These scores remain missing;32-photo monitoring is not a substitute |
| [Production speed](weak-detail-global-context-production-review-2026-11-16.md) | Runtime bottlenecks and proposed optimization sequence | Repeatable end-to-end baseline, then measured quality-preserving speedups; 100MP in 10 seconds remains unmet |

## Completed comparisons that guide the next work

| Question | Finding | Evidence |
| --- | --- | --- |
| How did the full-model continuation perform? | V131 improves broad photo PSNR by 0.04000 dB, with unseen-camera and severe ADC-color costs. Fixed ADC projection repairs color with a weak-band tradeoff | [Broad V131](v131-broad-primary.md), [ADC option](v131-adc-projection.md) |
| Does local RAW attention help at the full budget? | V132 at 20k loses 0.40978 dB faint ADC versus V131; ordinary detail is tied. The early 1k advantage did not persist | [Matched training](raw-spatial-continuation.md), [V132 endpoint](v132-endpoint-quality.md) |
| Do shared edges or better carrier allocation solve weak detail? | Shared-edge training is quieter but weakens response. Competing orientations help some weak sectors and hurt strong ones. Complementary proposals give a small lower-noise gain | [Shared-edge](shared-edge-comparison.md), [competing](competing-edge-response.md), [complementary](complementary-edge-response.md) |
| Does local support reduce false texture? | It lowers errors relative to global support; neural background prediction further reduces added error. Weak detail and small costs versus the parent remain | [Local full panel](local-wave-full-panel.md), [neural full panel](neural-nuisance-full-panel.md) |
| Does more local context or richer amplitude fitting suffice? | Larger background context loses weak response; local amplitudes increase response with severe building bands. Global background reduces those artifacts | [512-context ablation](neural-nuisance-context512.md), [local amplitudes](spatial-carrier-amplitudes.md), [global-background full panel](global-background-full-panel.md) |
| Does guided phase pooling generalize? | Weak response and full RGB error improve, but quiet/increment error worsens on the full eight-source panel; the pilot increment gain does not persist | [Full guided comparison](neural-guided-phase-full-panel.md) |
| Can extra fine frequencies restore the green fence faithfully? | Fine proposals make both directions more visible. Joint color support reduces tint; fresh signed-color wires still have no useful weak-response gain | [Fine proposal pilot](fine-frequency-proposals.md), [joint color](joint-fine-colour-support.md), [colored-wire validation](coloured-fine-wire-benchmark.md) |

V131 also changes the training cohort, so its gain is not an isolated test of
training duration. The new100k run has begun; its quality result remains
unmeasured. Its checkpoints use a100k schedule, distinct from the annealed20k
control. [Budget, source/crop/noise coverage and runtime evidence](full-corpus-scaling.md).

The synthetic panels differ in parents, sources, noise and metrics. Response
percentages from different rows are not a leaderboard. Both protected GFX scenes
remain required qualitative checks; their separate ISO100 references are not GT.
[Research rationale and literature](research.md).

## Running an experiment

Training recipes bind existing inputs and evidence by checksum. They are local
artifact recipes; the referenced caches/operator/checkpoints must be present.
Do not silently substitute missing sources or refresh their hashes.

```bash
source scripts/env.sh
uv sync --extra dev --extra nonlocal
uv run demosaic-experiment prepare configs/experiments/shared-edge.json \
  .cache/experiments/shared-edge
uv run demosaic-experiment inspect .cache/experiments/shared-edge
uv run demosaic-experiment audit-cache .cache/experiments/shared-edge
uv run demosaic-experiment train .cache/experiments/shared-edge --stop-after 8
uv run demosaic-experiment train .cache/experiments/shared-edge --resume
```

Use a fresh output directory for a new experiment. Preparation snapshots the
package and binds all inputs. Training uses that snapshot. Each committed row
includes head weights, Adam, EMA, RNG and frozen-state identity; resumption skips
the completed prefix. `launch` starts a detached worker with the same options.
[Configuration, export, evaluation and native-crop interfaces](architecture.md).

Reusable recipes include [V200 replay](../configs/experiments/v200-replay.json),
[shared-edge](../configs/experiments/shared-edge.json),
[competing orientations](../configs/experiments/orientation-balanced.json) and
[complementary proposals](../configs/experiments/complementary.json).
Their original completed runs and a fresh invocation of a recipe are separate
experiments; preparation alone does not launch training.

Quality review needs numerical checks and actual native viewing, including
present/absent detail, quiet/flat controls, natural photos and both GFX families.
A completed numerical producer is not a completed qualitative review.
[Evaluation protocol](evaluation.md).

## Historical experiment catalogue

The [pre-cleanup index](history/before-2026-11-17-cleanup/experiments.md),
[detailed research record](history/before-2026-11-17-cleanup/research.md),
[V200-era index](history/experiments-through-v200.md) and
[timestamped diary](../diary/index.md) preserve the longer sequence of trials.
Their running/queued statements describe their writing dates, not current jobs.
