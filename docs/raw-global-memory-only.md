# Memory-only global RAW features

**V139's experimental memory-only branch passes genuine CPU/CUDA16+2 checks;
trained reconstruction quality remains unmeasured.** Its original1k production
and matched native-quality review are now queued after V138's existing review
chain. The variant removes the direct local content/MLP bypass from the normalized
global branch. V120 remains the general recommendation.

[Implementation](../src/demosaic/raw_global_memory_features.py) ·
[Tests](../tests/test_raw_global_memory_features.py) ·
[1k recipe](../configs/quality-v120-raw-global-memory-only-pilot-v139.yaml) ·
[Implementation-check driver](../scripts/check_global_memory_only_pilot.py) ·
[Measured checks and independent audit](results/raw-global-memory-only-checks-v1.json) ·
[Check publication](results/raw-global-memory-only-publication-v1.json) ·
[Training/review queue](results/raw-global-memory-only-queue-v1.json) ·
[Queue verification](results/raw-global-memory-only-queue-publication-v1.json).

## Why remove the shortcut

The [trained V137 intervention](global-memory-contribution.md) finds that memory
write contributes only0.83–1.39% of the branch-offset RMS on six retained
contexts. Spatially varied attention alone did not produce clear fine-mesh
recovery. [V138](raw-global-only-training.md) already queues the normalized
branch with a frozen parent and larger branch LR; its quality remains pending.

V139 tests a separate architectural hypothesis: direct local content and its
feed-forward correction may let the branch optimize without learning useful
global matching. Removing them gives the memory path a direct learning role.
This hypothesis is not established by the V137 ablation, and forcing this path
does not ensure useful matching or improved photographs.

Both variants retain64 memory slots,32 channels, four attention heads,
cosine-normalized queries/keys and per-image amplitude scaling. V139's returned
features pass through both the content-to-memory and memory-to-pixel attention
operations. The inherited expansion/pixel-shuffle/zero projection supplies64
native RGB-stem feature offsets, rather than a separate RGB prediction.

Only `up.weight`, `down.weight` and `ff_gain` are removed:18→15 tensors,
18,272→14,144 parameters. All fifteen shared deterministic initial tensors
equal the conditioned branch. Constructor RNG is preserved. Bias-free values
and signed differences keep each per-phase spatial constant exactly zero after
adaptation, including spatially varying noise conditioning. The final projection
starts at zero, retaining the parent model's initial output.

## Configuration and compatibility

Select this operator explicitly:

```yaml
raw_global_only: true
model:
  raw_global_features: true
  raw_global_conditioning: memory-only-v3
```

The complete recipe also specifies native anchored/stabilized RGB restoration,
official frozen DINOv3 ConvNeXt-Small and physical FP32 arithmetic. Missing mode
still selects `legacy-v1`; `cosine-rms-v2` keeps its existing operator.
Changing modes on resume rejects before model construction. Tensor layouts also
differ, so learned weights cannot silently lose their local path on loading.

The independent source audit compares all67 existing neural modules against the
new68-module snapshot:64 files are byte-identical. In the other three, AST
changes are confined to the two operator-selecting constructors and the explicit
resume validator. Existing forward mathematics is unchanged, and all existing
jobs retain their original frozen sources and plans.

## Genuine implementation checks

Both phases start freshly from the V12020k Small EMA. The original1k cosine
horizon stays fixed while each discarded check executes16 updates and a real
two-update resume. CPU uses128px/B1/FP32; CUDA uses256px/B16/BF16 with physical
and feature arithmetic in FP32. The frozen-parent scope selects exactly15 Adam
states and106 model/EMA tensors; all91 parent tensors stay exact in both model
and EMA at16 and18.

| Check | CPU | CUDA |
| --- | ---: | ---: |
| Root/encoder/optimizer calls each |18 |18 |
| Unique target contexts |18 |288 |
| Prepared-array values equal to saved control |2,507,076 |160,437,312 |
| Initial RGB/auxiliary values equal |65,536 |4,194,304 |
| Independently rehashed prepared batches |18 |18 |
| Changed-setting resumes rejected before construction |7 |7 |

All15 branch tensors receive finite nonzero gradients during each18-update
check. Initial feature offsets contain68,157,440 exactly zero values across the
two phases. The independent saved-artifact audit checks263,464,044 finite
model/EMA/Adam values across four retained16/18 checkpoints, every prepared
array against saved V137, initial outputs and540 gradient metadata fields.
Gradient arrays/backward derivatives are not independently recomputed.

All36 logged clean/noisy hashes match the saved input control; clean arrays
before preparation were not separately retained. The audit independently
rehashes every prepared batch and compares its actual tensor values.
V137 is an input/initialization control here. The intended trained architectural
comparison is V138, which shares V139's LR1e−3 and frozen-parent scope.

CUDA peak allocation is7,929,051,648bytes under the16GiB cap. CPU/CUDA admission
uses40/52GiB available memory and the32GB training runtime floor. These are
resource observations, not speed benchmarks. The focused78-test suite covers
independent attention mathematics, no local bypass, all-CFA constants, batch
isolation, gradients, portable branch reload, parent/EMA freezing and mode guards.

## Queued training and quality comparison

The original1k recipe changes only the operator against V138: same
90,782 photos/27 reviewed regions, seed70,50% reviewed quota, corrected paired32
and native128 catalogues, single-view loss, zero optical blur, LR1e−3 and100-step
warmup. The newer90,774/36 bank remains available separately. The checks end
during warmup and do not prove stability at peak LR or convergence.

The [production driver](../scripts/train_memory_only_pilot.py) adopts exact
copies of the completed CPU/CUDA16+2 receipts. It runs no additional checks and
starts production freshly from V120, rather than resuming either discarded
prefix. The original1,000-update cosine horizon remains fixed. The controller
waits for the existing V138 primary/faint/memory chain and its exact memory
owner to finish within that dependency's original deadline. It then requires
52GiB available RAM and128/208GiB internal/external free space for15s, with a
2h headroom limit,16GiB CUDA cap,32GB runtime floor and8h worker limit.
No score threshold or human publication gate controls this admission.

The fresh run adds1,000 optimizer/forward calls,64 validation calls and1,064
encoder calls over16,000 target slots. Every clean/noisy batch matches saved
V137 before candidate inference; endpoint binding additionally compares all
1,000 actual V138 clean/noisy hashes. It requires106 finite model/EMA tensors,
15 Adam states at1k, all91 frozen parent tensors exact and all68 trained neural
source files equal to the inference snapshot.

The separately live review queue declares **102 new candidate root/encoder
calls**:64 shadow,16 ordinary,16 faint ADC, four main-GFX512 contexts and two
extra-mesh768 fixed profiles. It reuses510 V120/V129/V136/V137/V138 predictions,
checking the actual V138 observation records before adopting its102 outputs.
There is no control-model replay, new noise, RAW decode, fitted exposure or
conditioning sweep. Collection uses IEEE FP32,52GiB admission,12GiB CUDA cap
and32GiB runtime floor. CPU stages require40GiB; each headroom wait is bounded.
The new quality deadline is the original V138 memory deadline plus24h; no
original deadline changes.

The prospective report has576 metric rows/144 groups and64 primary native PNGs,
including two exact-GT triplets, ordinary/faint/shadow detail, DSCF3879/3880
foliage/fence/sky/building and corrected DSCF3842/DSCF3835 mesh. A six-method
faint supplement uses the same source-defined masks, DC/spatial errors and40×
display. Four mesh boards include both camera JPEGs with a common+4EV scalar-LUT
check. Independent FFT/native-pixel audits follow; actual native viewing and
publication remain required after execution. Real ISO100 and native binned
references retain their approximate roles, and all protected captures/siblings
remain outside training.

Sixteen new handoff tests pass. A zero-forward preflight verifies the adopted
checks,68 source modules,102 unchanged observations, unchanged scoring helpers
and derived report budgets. Invoking the actual endpoint binder against live,
incomplete training rejects before any checkpoint or neural load.

This is a1k development pilot, not the full427-photo or measured-camera/color
panel. Those broader comparisons, tiled seams/full frames, speed and broad
real-camera superiority remain unmeasured. The original checkpoints, receipts,
source bytes, schedules and other training/review owners remain intact.
