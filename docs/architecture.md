# Architecture and experiment workflow

The November 15 consolidation gives new work a shared package and a configured
runner. The historical numerical primitives, published model weights, source
snapshots and machine receipts remain intact. This is an engineering change;
V120 remains the general recommendation and the mesh/quiet-field problem is
still open. [Current choices](current-model.md).

## Package boundaries

| Package | Responsibility |
| --- | --- |
| `demosaic.models.registry` | Named model choices, checkpoint identity and loading |
| `demosaic.models.compat` | Historical initialization and checkpoint formats |
| `demosaic.models.wave` | Composed matching, pooled-wave and innovation stages |
| `demosaic.experiments.artifacts` | Input digests, exclusive JSON publication and source snapshots |
| `demosaic.experiments.runtime` | Process ownership, resource limits and deterministic settings |
| `demosaic.experiments.data` | Procedural/paired targets, sensor coupling and checked cache streaming |
| `demosaic.experiments.objectives` | Reconstruction, flat, pair and directional loss terms |
| `demosaic.experiments.checkpoints` | Trainable head state, frozen-state identity, Adam, EMA and RNG |
| `demosaic.experiments.training` | One cached-head training loop |
| `demosaic.experiments.evaluation` | Established metrics, exact arrays and native crop triplets |

The new packages import no experiment scripts. Sixteen former helper modules
under `scripts/` now alias the packaged modules, including private names and
module assignments used by old callers. Historical trial entry points stay in
place because published plans bind their paths and frozen import closures.
They are compatibility/reproduction tools; new experiments use recipes.

The older full-model trainer and `JointDemosaic` configuration remain available
for broad photo/camera training and historical checkpoints. The shared runner
currently consolidates cached head experiments, not every historical training
regime. A future full-model experiment should extend the shared runtime instead
of copying another versioned script.

## Composed model stages

The V187/V195 pooled component now executes as a `PooledWaveStage` containing a
frozen `MatchingStage` and a wave readout. V198/V200 execute as an
`InnovationWaveStage` containing that frozen pooled anchor, physical RAW
measurements and a trainable readout. Zero supplied variance preserves the
same inherited pixels and bypasses the same branches.

Historical constructors are used once at the compatibility boundary to retain
the exact seeded initialization. Their modules are adopted by the composed
model; subsequent forward calls do not dispatch through the nine-class trial
inheritance chain. Existing frozen restoration/readout primitives are retained.
`legacy_state_dict` and `load_legacy_state_dict` explicitly translate tensor
names; the new internal names describe the composed stages. Shape/dtype checks
precede loading. No old checkpoint is rewritten.

Use `demosaic.models.registry.load_model("v120")` for the declared general model.
Experimental presets require an explicit component checkpoint unless a default
is published. These components consume cached base-restoration RGB plus RAW;
they do not replace the full-frame parent by themselves.

The experimental `orientation-balanced-cfa-wave` kind uses that same composed
stage with an explicit selector from `demosaic.competing_phase`. It allocates four
carriers to each of two angular proposals with `family_degrees: 20`, retaining
the original eight-carrier budget and 643 trainable parameters. Its exported
`module_config` carries this setting. Existing kinds use the original selector.
[Intervention and measured limits](competing-wave-candidates.md).

## Running an experiment

```bash
source scripts/env.sh
uv sync --extra dev --extra nonlocal
uv run demosaic-experiment models
uv run demosaic-experiment prepare configs/experiments/shared-edge.json \
  .cache/experiments/shared-edge
uv run demosaic-experiment inspect .cache/experiments/shared-edge
uv run demosaic-experiment audit-cache .cache/experiments/shared-edge
uv run demosaic-experiment train .cache/experiments/shared-edge --stop-after 8
uv run demosaic-experiment train .cache/experiments/shared-edge --resume
```

`launch` accepts the same run/resume/stop arguments and starts a detached worker
with a log. Preparation binds the recipe, caches, initializer, operator library
and evidence by SHA256, and snapshots package code. Relative input paths are
resolved against the recipe directory. Checksum fields are checked rather than
silently refreshed. Execution uses the snapshot, independently of later edits.
Preparation and metadata inspection initialize no CUDA context.

Recipes make the model, initialization, domain weights, complete LR horizon,
runtime policy and resource reserves explicit. The shipped V200 replay recipe
uses the original observations and schedule. The shared-edge recipe substitutes
the completed audited cache; matched training and its
[raw/EMA quality review](shared-edge-comparison.md) are complete. Neither recipe
launches merely by being prepared. Cached training performs no parent
DINO inference, source loading or new noise draws.

Every completed schedule row is atomically published with its summary,
trainable tensors, Adam, EMA, frozen-state hash and Python/NumPy/Torch/CUDA RNG.
ADC-only rows are recorded without a forward or optimizer update. `--resume`
validates the contiguous committed prefix and starts at the next row. Reporting
failure after a commit does not replay that row. An OS lock prevents two workers
from updating one run and releases automatically if a process exits.

```bash
uv run demosaic-experiment export .cache/experiments/shared-edge \
  .cache/experiments/shared-edge-EMA.pt --state ema
uv run demosaic-experiment evaluate .cache/experiments/shared-edge \
  /path/to/quality-design.json .cache/experiments/shared-edge-evaluation --state ema
```

Export/evaluation require a completed run. Exports retain historical tensor
names and record the source checkpoint and plan. Evaluation accepts the existing
`observations` schema with checked `arrays` and `parent` bindings, uses the
established 512-context/160-ROI metrics, and saves lossless native predictions.
Real independent references are not scored as exact GT. Numerical evaluation
does not replace the complete matched review, both raw/EMA endpoints, protected
GFX scenes, native inspection or export checks required for a quality report.

`evaluation.crops.write_triplet` publishes unchanged crop pixels with a shared
FP64 display transform, ROI, source, checkpoint, noise coefficients, exposure,
WB/matrix and explicit exact/independent/approximate reference labels. Crop
pixels are never resized.

## Compatibility and validation

Focused tests cover legacy aliases, physically coupled target generation,
all-CFA composed output/auxiliary/gradient parity, strict checkpoint conversion,
ADC routing, immutable publication, ownership and uninterrupted-versus-resumed
Adam/EMA/RNG equality. Real saved V200 raw/EMA checkpoints also reproduce the
old implementation bit-for-bit on a cached native64 crop, without parent
inference or noise draws. An eight-row CUDA replay also reproduces the original V200 step8 checkpoint:
all 643 head parameters, EMA, Adam and CPU/CUDA RNG are bit-exact after seven
updates and one ADC skip. The shared-edge prepared run passes its complete
1,000-row cache audit. The real CLI completes prepare/stop/resume/EMA export on
a discarded four-row CPU fixture. There are 427 passing tests across 27 affected
modules; Ruff and wheel content/import checks pass.
[Validation receipt](results/consolidation-validation-v1.json) ·
[CUDA replay](results/consolidation-v200-CUDA-replay-v1.json).
These are implementation checks, not new quality or full-frame speed measurements.

Keep new tests at these behavioral boundaries. Historical studies and all their
receipts remain linked from the [experiment archive](history/experiments-through-v200.md)
and [diary](../diary/index.md). Archived running/queued prose is historical;
current operational state belongs in [the current experiment page](experiments.md).
