# Matched normalization trial: CUDA preflight passed, first1k training running

V68 control and V69 augmentation start from the same genuine V63 original20k
EMA. They test whether training with varied physical feature coordinates reduces
the color/coarse failures found in the [completed20k review](long-commons-v63-v64-original20k-review.md).
**Trained quality is unknown.** The working reference remains V43.

[Executed CUDA checks, independent artifact audit and actual launch](results/normalization-augmentation-CUDA-and-launch.json).
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
guards. Both arms stop at1,000 of their planned4,000 updates; there is no
automatic continuation or promotion.

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

Full quality evaluation is not yet queued at this launch capture. It must compare
both new arms against each other and their parent on the fixed427 panel plus
the frozen418/416 sensitivities, paired domains, analytic/color diagnostics and
native real crops. Reports need at least two native photographic triplets per
model and accurately labeled standing GFX sky/building/foliage/fence references.
Neither selected training loss nor this preflight permits a quality promotion.
