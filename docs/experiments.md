# Current experiments

**The matched shared-edge trial completed all 900 updates and 100 ADC skips
(November 16), and its full quality review is complete.** All 1,000 committed
rows passed the checkpoint/Adam/frozen-state audit. Both endpoints completed all
822 existing inputs; all 60 native boards/12 triplets were actually inspected.
The result has small quiet/flat gains, lower mesh response and persistent real
fringes/incomplete crossings. [Complete comparison](shared-edge-comparison.md).
[Training completion](results/shared-edge-training-completed-v1.json) ·
[Launch observation](results/shared-edge-launch-v1.json) ·
[Current model choices](current-model.md).

| Recipe | Purpose | State |
| --- | --- | --- |
| [V200 replay](../configs/experiments/v200-replay.json) | Original V200 initialization, observations, loss and complete LR schedule | Existing original study complete; new runner recipe ready |
| [Shared-edge](../configs/experiments/shared-edge.json) | Same head/loss recipe with paired strong-edge backgrounds and faint mesh increments | Training and full two-endpoint native review complete; [measured tradeoff](shared-edge-comparison.md) |
| [Fresh-noise finite-wire panel](near-edge-response.md) | Independent zero/one/two-direction roles, near/far edges, all CFAs | Nominal 384-observation review complete; lower-noise ISO1600/ISO400-prior evaluations running sequentially |

Both recipes bind existing inputs and evidence by checksum. They are local
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

The shared-edge intervention changes generic scene content and coupling
together. It addresses the [observed coverage gap](paired-training-coverage.md),
not an established cause of the current artifacts. A quality report still needs
the complete matched present/absent/quiet/flat/photo suite, raw/EMA endpoints,
both protected GFX families and native triplets with accurate references.
The review controller does not restart training or promote a model; its terminal
numerical result explicitly leaves actual native viewing pending. Paired metrics
match case identities and conditions, retain error tails, and exclude independent
real references from exact-GT scoring.

The [analytic withheld-CFA diagnostic](withheld-cfa-evidence.md) has completed:
3,072 A/B fits, fixed threshold curves and source-cluster summaries. It rejects
the tested flat-noise candidates but exposes predictable edge leakage, especially
when step geometry is misspecified. This CPU-only result changes no neural
checkpoint or recommendation.

The [edge-refinement follow-up](withheld-cfa-edge-refinement.md) completes 7,168
matched analytic fits. At thresholds selected on calibration nulls alone, both
arms have zero observed test-null activations; off-grid weaker-direction gain
rises from 2.39% to 56.99%, with lower exact increment error. Two native exact-GT
triplets and the unchanged-control checks accompany this restricted result.

Historical study entry points remain for reproduction. Their reusable helper
imports now resolve to packaged implementations; original frozen snapshots are
unchanged. The complete [earlier experiment index](history/experiments-through-v200.md)
and [timestamped diary](../diary/index.md) retain previous results and decisions.
