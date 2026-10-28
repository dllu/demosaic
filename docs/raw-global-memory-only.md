# Memory-only global RAW features

**V139's experimental memory-only branch passes genuine CPU/CUDA16+2 checks;
trained reconstruction quality remains unmeasured.** It removes the direct
local content/MLP bypass from the normalized global branch. V120 remains the
general recommendation. No V139 production controller or image-quality
collection has been launched.

[Implementation](../src/demosaic/raw_global_memory_features.py) ·
[Tests](../tests/test_raw_global_memory_features.py) ·
[Future1k recipe](../configs/quality-v120-raw-global-memory-only-pilot-v139.yaml) ·
[Implementation-check driver](../scripts/check_global_memory_only_pilot.py) ·
[Measured checks and independent audit](results/raw-global-memory-only-checks-v1.json) ·
[Publication verification](results/raw-global-memory-only-publication-v1.json).

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

## Quality comparison still required

The declared future1k recipe changes only the operator against V138: same
90,782 photos/27 reviewed regions, seed70,50% reviewed quota, corrected paired32
and native128 catalogues, single-view loss, zero optical blur, LR1e−3 and100-step
warmup. The newer90,774/36 bank remains available separately. The checks end
during warmup and do not prove stability at peak LR or convergence.

A longer trial needs the matched V138 result and retained native/photo/camera/
color comparisons. Its report must include two exact-GT native triplets,
ordinary/faint/shadow detail, DSCF3879/3880 foliage/fence/sky/building and the
corrected DSCF3842/DSCF3835 mesh with both camera JPEGs. Real ISO100 and native
binned references retain their approximate roles. Tiled seams/full frames and
broad real-camera superiority also remain unmeasured for this variant.
