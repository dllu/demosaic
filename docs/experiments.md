# Current experiments

The consolidated cached-head runner is ready for new trials. **The shared-edge
training-data cache is complete and audited; trained quality is unmeasured.**
The November 15 cleanup launches no production training and changes no model
recommendation. [Current model choices](current-model.md).

| Recipe | Purpose | State |
| --- | --- | --- |
| [V200 replay](../configs/experiments/v200-replay.json) | Original V200 initialization, observations, loss and complete LR schedule | Existing original study complete; new runner recipe ready |
| [Shared-edge](../configs/experiments/shared-edge.json) | Same head/loss recipe with paired strong-edge backgrounds and faint mesh increments | 156 changed rows/844 exact adoptions cached and audited; model not trained |

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

Historical study entry points remain for reproduction. Their reusable helper
imports now resolve to packaged implementations; original frozen snapshots are
unchanged. The complete [earlier experiment index](history/experiments-through-v200.md)
and [timestamped diary](../diary/index.md) retain previous results and decisions.
