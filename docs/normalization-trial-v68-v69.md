# Matched normalization trial: first1k reviewed, original4k continuation selected

V68 control and V69 augmentation start from the same genuine V63 original20k
EMA. They test whether training with varied physical feature coordinates reduces
the color/coarse failures found in the [completed20k review](long-commons-v63-v64-original20k-review.md).
The [completed first1k review](normalization-v68-v69-first1k-review.md) finds a
small +.00621dB matched photo gain with unresolved texture/color failures.
Neither endpoint is promoted. The working reference remains V43.

[Executed CUDA checks, independent artifact audit and actual launch](results/normalization-augmentation-CUDA-and-launch.json).
[Completed training boundaries and actual review/recovery](results/normalization-first1k-review-queue.json).
[Coordinate diagnosis, implementation and earlier CPU checks](normalization-augmentation.md).

V63 is the initializer because its photo mean is close to V64 and its checked
bright-color groups have lower bias/RMSE. That parent selection is a research
choice informed by the completed review, not a blind comparison. Both trial arms
use the same parent, so their matched difference tests the normalization policy.

| Setting | V68 control | V69 augmented |
| --- | --- | --- |
| Training normalization | Full-context statistics | Stateless half-probability center-half statistics |
| Initializer | V63 original20k EMA | Same |
| Optimizer/EMA | Fresh AdamW/EMA | Same |
| Planned horizon / first gate |4,000 /1,000|Same|
| Seed / LR / warmup |50 /3e−6 /100|Same|
| Batch / native patch / precision |16 /256 /BF16|Same|
| Commons / native / paired data |40,170 /128 captures /32 prepared pairs|Same|
| Domain fractions |25% paired /25% native /50% Commons/procedural|Same|
| Data path |4×→geometry/PSF→area2, original noise/ADC/wide8 palette|Same|
| Ordinary inference |Original full-context normalization|Same|

Only normalization policy, run path and notes differ between the
[control recipe](../configs/dino-convnext-normalization-control-b16-v68.yaml) and
[augmented recipe](../configs/dino-convnext-normalization-augmented-b16-v69.yaml).
The separately prepared larger corpus is unused. This is a new fine-tuning
experiment, with fresh optimizer/EMA; it does not resume/retime the closed20k
optimizer or modify its checkpoints. First1k uses the original new4k learning-rate
curve, followed by a quality review before continuation.

Initializer SHA256:
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
Frozen producer source bundle:
`db5fb3ba42827e9db043dbc85f069bb1e5568cdafa872f7340d872852bc6a771`.

## Genuine CUDA engineering checks

The [preflight operator](../scripts/preflight_normalization_cuda.py) executes
six discarded production-size updates per arm: control, augmentation, and
3+3 interrupted/resumed augmentation. Batch16/native256/BF16, real data,
workers4+2+2 and the4k horizon match the prepared recipes; only fixture logging,
checkpoint and small validation settings differ. All three data domains occur.

- All18 updates have89 finite trainable gradient tensors. All three final
  states have finite91 model/91 EMA/89 Adam tensors/states; all89 model and EMA
  parameter tensors change, while the two context buffers remain exact.
- Before the first fetch, fresh runs exactly match the parent's EMA and fresh
  optimizer. The resumed run exactly restores model, optimizer and all three
  RNG families. The pre-update EMA matches the expected state in all four legs.
- All six input fingerprints, domains and learning rates agree across control,
  augmentation and resume. Each augmented batch has both coordinate choices;
  independent SHAKE256 recomputation checks every16-image mask.
- Genuine frozen DINO stays gradient-free and hash-identical:
  `370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
- The four-CFA transformed-feature CUDA fixture matches its CPU oracle exactly
  within the predeclared3e−6 absolute/relative bounds. The zero-mask CUDA path
  is bitwise equal to default, preserving RAW/canvas/RNG.
- Ordinary FP16 EMA loading matches manually restored EMA predictions exactly
  on both fixed photos for both augmented endpoints. Inference uses the
  original normalization, with no training mask.

The independent CPU-only artifact audit rechecks input/helper/source hashes,
rebuilds source bundles, verifies saved finite states and masks, and confirms
saved full/resumed RNG/config equality. It loads no model and performs no new
inference. Full-versus-resumed CUDA optimization is **not bitwise identical**:
observed maximum model/EMA differences are2.38e−7/1.64e−7. These are reported
observations, not a deterministic-optimization quality criterion. Peak CUDA
allocation is7.213GB, not total unified RAM. The10 normalization unit tests and
Ruff also pass. These engineering checks do not establish restoration quality,
convergence or production throughput.

Actual fixture/independent audit:
`/mnt/external/demosaic/benchmarks/normalization-augmentation-CUDA-v1/`.

## Actual first1k launch

The serial controller launched as PID497608/creation1792256805.99; V68's first
child is497625/1792256808.06. These are launch identities; check actual processes
before acting. The first production input fingerprint/domain/LR match the
discarded genuine control fixture. Loss/gradient arithmetic is not claimed
bitwise deterministic. The package, recipes and inputs have157 frozen file
guards. Both arms have now stopped and passed their1,000-update boundaries;
the controller has exited. Their full planned horizons remain4,000. All41
logged observation/domain/LR fields match across arms. There is no automatic
continuation or promotion.

Immutable first1k checkpoint SHA256:

- V68 control: `456a5fb245bc807d91470cbb067e137ea48ace8eb5796a3d6ad9218573d9ad0c`.
- V69 augmented: `6f34be8b2cc4fbba1116b4ed17bbafe41d5526da928238d194b6355b9b8b665c`.

Operational files:

- Status: `/mnt/external/demosaic/runs/normalization-v68-v69-first1k-workflow-v1.json`.
- Plan, frozen package/controller, logs and boundary receipts:
  `/mnt/external/demosaic/benchmarks/normalization-v68-v69-first1k-workflow-v1/`.
- Runs: `/mnt/external/demosaic/runs/dino-convnext-normalization-{control,augmented}-b16-v{68,69}/`.

The boundary checks verify planned/actual step counts,91/91/89 finite state,
parent/source/data/recipe identity, exact context buffers, the4k LR curve and
logged augmentation masks. Across both arms, all41 logged input/domain/LR rows
must agree. Older parent model-config fields are compared with their explicit
default values; the newly added RAW-kernel defaults stay disabled.

## Completed full first1k review

[Performance report and decision](normalization-v68-v69-first1k-review.md).
[All81 actual native views](normalization-v68-v69-first1k-native-gallery.md).
[Statistics, artifacts, hashes and preserved recovery records](results/normalization-v68-v69-first1k-review.json).

The shared-source review covers432 known/540 unseen/74,424 full427 cases,
1,792 analytic cases, three full GFX outputs/six RGB16 files,18 other-camera
crops and96 selected CPU-color predictions. All36 comparisons/nine classical
witnesses and27 frozen source-sensitivity comparisons pass their audits.
The fresh hue grid has4,704 predictions,28,224 audited case fields and864
independently checked group scalars. No old-source hue arrays are reused.
All81 native originals were actually viewed, with matching noisy/reference
pixels across26 observation groups. Reports include two native photographic
triplets per model and GFX foliage/fence alongside sky/building detail.

The v1 wrapper import failure, v2 hue inference-mode failure and v3 recovery
path rejection remain preserved. V4 successfully reuses closed panels and
statistics byte-for-byte, computes hue in a new output directory and completes
all artifact/source audits. Numerical bounds, model/data/kernel and completed
outputs remain unchanged. Direct library inference mode is now covered by a
regression test; the pure lineage helper identifies the verified parent by SHA.

Completed review status:
`/mnt/external/demosaic/runs/normalization-v68-v69-first1k-review-workflow-v4.json`.
Plan/controller/logs:
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-first1k-review-workflow-v4/`.
Previous failed directories/statuses remain historical evidence.

The first1k policy effect is small and mixed: photo/procedural means increase,
but real-camera differences, lost texture and bright hue failures prevent
promotion. The explicit quality decision is to finish the originally planned
4,000 updates from complete model/EMA/Adam/RNG state, using separate continuation
run directories to preserve first1k artifacts. Data, seed, LR horizon, frozen
source and policy remain fixed. No new training budget or corpus is introduced.
The completed4k endpoints need a new full review before any promotion.

## Actual original4k continuation

[Restored production state and actual launch](results/normalization-original4k-continuation-launch.json).
At the launch capture, V68 control had resumed from step1,000 and passed
step1,025. The actual model,
all89 Adam states and Python/Torch/CUDA RNG families match the saved checkpoint
before the first data fetch. EMA matches before its first update; frozen DINO
has its expected hash and stays gradient-free. These read-only checks execute
inside the production run, without discarded training updates. V69 follows
serially after control completes. All1k checkpoints/logs/review stay unchanged;
the only recipe change is a separate output run directory. The original4k LR
curve, source bundle, data, seed and normalization policies remain fixed.

The first continuation wrapper missed the spawn-worker main guard and made
zero updates. Only its exact owned failed trainer process group was stopped;
the failed status/log/run directories remain intact. The corrected frozen
wrapper passes a CPU import under`__mp_main__` without training/file writes/
CUDA initialization, then resumes in fresh v2 directories. No original checkpoint,
data, model or numerical bound was changed to recover.

Actual launch identities: controller622973/1792260581.40 and control
trainer623004/1792260584.48. These are historical launch identities; verify
current status and creation times before acting. Operational status:
`/mnt/external/demosaic/runs/normalization-v68-v69-original4k-continuation-v2.json`.
Frozen plan/controller/production wrapper and logs:
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-continuation-v2/`.
The183 frozen guards also bind the preserved first1k inputs and completed review.
The launch receipt predates the full4k review queue below. Both4k boundaries,
matched new input/LR checks and the next full/native quality review remain work.
There is no automatic post4k continuation or promotion.

### Control completed, augmented arm resumed

[Actual4k control boundary and augmented handoff](results/normalization-original4k-control-complete-handoff.json).
V68 has completed its original4,000 updates and exited. Its controller audit
passes91 model/91 EMA/89 Adam finite state, complete RNG, original162 logged
steps/LRs, source/data/recipe/parent identity and exact1k log prefix. All89 model
and EMA parameter tensors changed since1k; the two context buffers remain exact.
Frozen checkpoint SHA256:
`5bcb45adb6ace6aed3cd2071ad56f36bd019645ec4c117c4d6f65beda220b737`.

V69 is now training from its genuine1k state. Production checks verify exact
model/all89 Adam/RNG restoration before first fetch and EMA before its first
update. Frozen DINO has the expected unchanged hash. All52 available logged
observation/domain/LR rows, including the original1k prefix and through step1,250,
match control exactly. Augmented masks are independently recomputed. This is a
partial matched-input check; the complete162-row proof still needs V69's finish.
The183 frozen guards and the actual control checkpoint/log/receipt hashes are
revalidated. These are training-state milestones, not a performance report.

Actual augmented trainer at handoff:658410/1792262498.98 under the same
controller622973/1792260581.40. The full review remains waiting behind both arms;
there is no quality promotion or change to data, LR horizon, source or policy.

## Queued full4k review

[Actual waiting controller, frozen plan and verified components](results/normalization-original4k-review-queue.json).
The review is queued behind the exact live continuation owner and starts only
after both original4k boundaries pass and that owner exits successfully. The
completed-boundary reader verifies the actual4k checkpoint hashes,162-row logs,
restoration receipts, frozen training guards and reviewed first1k decision.
Live, partial, failed and wrong-step states cannot release inference.

Parent/control/augmentation get the same fresh primary evaluation:432 known,
540 unseen and74,424 full427 cases,1,792 analytic cases, three full GFX outputs/
six RGB16 TIFFs,18 other-camera crops and96 selected CPU-color predictions.
The60 statistics/fifteen classical witnesses include each candidate versus its
own1k checkpoint, in addition to matched policy and parent comparisons. The
frozen427/418/416 source cohorts yield45 photographic sensitivity comparisons.

The hue grid needs2,352 new candidate predictions and reuses2,352 independently
audited parent/nonlocal-reference arrays. Source, observation, precision and
checkpoint gates are unchanged; each reused array's hash is checked when read.
These parent/reference arrays share the exact frozen producer source with this
continuation, as verified by the actual compatibility check. The source mismatch
that required fully fresh hue inference at1k does not apply to this4k run.

An engineering replay on actual completed1k six-method panels reproduces all36
existing nonself statistics exactly; all24 same-weight progress statistics are
zero, with15 witnesses total and no new inference/CUDA. It is not a4k result.
The actual live4k gate rejects execution. Thirty focused tests and Ruff pass.
Imports and wrapper signatures are also checked against the actual frozen
package on CPU, avoiding the previous wrong-import wrapper failure.

Actual queued review owner:638004/1792261092.43. It was verified live with no
child processes at publication. Its115 frozen file guards bind the operators,
wrappers and inputs. Operational status:
`/mnt/external/demosaic/runs/normalization-v68-v69-original4k-review-workflow-v1.json`.
Frozen plan/controller/tools/logs:
`/mnt/external/demosaic/benchmarks/normalization-v68-v69-original4k-review-workflow-v1/`.
The status is mutable; the public receipt includes an immutable capture.

All81 future native views remain manual:57 primary,12 hue, six supplementary
GFX and six selected CPU-color triplets. At least two exact-GT photo triplets
per model and the standing GFX sky/building/foliage/fence references are required
in the final report. These counts and evaluations are planned, not completed
quality evidence. No automatic promotion or training beyond4k is queued.
