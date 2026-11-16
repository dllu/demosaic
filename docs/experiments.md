# Current experiments

**The matched shared-edge trial is training (November 16); quality is still
unmeasured.** A live controller will audit the committed training rows, export
both raw/EMA endpoints, evaluate all 822 existing inputs and retain all 60 native
boards/triplets with the original coordinates and display choices.
[Launch observation](results/shared-edge-launch-v1.json) ·
[Current model choices](current-model.md).

| Recipe | Purpose | State |
| --- | --- | --- |
| [V200 replay](../configs/experiments/v200-replay.json) | Original V200 initialization, observations, loss and complete LR schedule | Existing original study complete; new runner recipe ready |
| [Shared-edge](../configs/experiments/shared-edge.json) | Same head/loss recipe with paired strong-edge backgrounds and faint mesh increments | Training in `.cache/experiments/shared-edge`; matched review queued in `.cache/experiments/shared-edge-review` |

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

Historical study entry points remain for reproduction. Their reusable helper
imports now resolve to packaged implementations; original frozen snapshots are
unchanged. The complete [earlier experiment index](history/experiments-through-v200.md)
and [timestamped diary](../diary/index.md) retain previous results and decisions.
