# Joint restoration training from completed V66

V67 is a separately initialized joint restoration-training stage, following the
[completed V66 review](raw-kernel-phase-v66-first1k-review.md). V66 improves its
matched head warmup but remains grainy and far below mature V60. Both head
warmups froze the existing restoration features. This motivates testing joint
optimization, without claiming those frozen features caused the quality deficit.
The [completed2k review](raw-kernel-phase-joint-v67-first2k-review.md) finds photo+2.81345dB over V66, still3.32464dB below mature V60, with remaining grain/weak-detail loss. **No promotion; V43 remains the working reference.**

[Recipe](../configs/dino-convnext-raw-kernel-phase-joint-b16-v67.yaml).
[Executed preflights](results/raw-kernel-phase-joint-v67-preflight.json).
[Actual launch, owners, immutable plans and queues](results/raw-kernel-phase-joint-v67-launch.json).

V67 starts from completed V66 step1000 **EMA**, with fresh AdamW/EMA. It trains
all92 restoration parameter tensors/32,931,920 parameters, including the RGB
feature network, measurement adapter, DINO feature-fusion layers and three RAW
head tensors. The actual DINOv3 ConvNeXt backbone remains frozen. Its parameters
are omitted from restoration checkpoints and loaded at the pinned revision.
Two normalization buffers remain fixed. This is initialization into a new run,
not resuming the incompatible three-state head-only optimizer.

The physical reconstruction and model code remain unchanged: bilinear plus
learned, bounded same-color RAW-difference coefficients, conditioned directly on
CFA/native phase. There is no free RGB output offset. Clean constant-color fields
retain their invariant; noisy coefficient estimation can still bias or amplify
noise. Source bundle:
`fc0297db08d659523fdcefe1ef0e7a4da12ae97f648e95b1579db65de93d268a`.
Parent checkpoint SHA256:
`df88bbc32c370754a5915eb1e49b9ce69ddef272ae816939b7cc40b49aa5b79c`.

The declared original schedule is **10,000 updates**, seed50, LR1e-4/warmup100.
The trainer stops at **2,000** for a frozen full review, preserving the original
10k cosine schedule. There is no automatic continuation. B16/native256/BF16,
workers4+2+2, original40,170 Commons/native128/paired32, fractions, wide8 palette,
geometry/noise/validation all stay fixed. Geometry still precedes the final2×
area reduction and loaders fetch selected domains. Initialization/scope/seed/LR/
budget differ from V66; historical differences cannot isolate unfreezing alone.

## Executed engineering checks

The genuine-parent CPU fixture uses B1/native64/FP32, workers0, forced smooth
Commons and two validation images. It loads all94 V66 EMA tensors exactly and
reproduces two initial full-photo predictions through the portable loader. Seven
updates exactly match3+4 resumed updates in nine saved fields and every numeric
log/input hash. Finite94 model/94 EMA/92 AdamW states and all optimizer steps pass.
All92 restoration tensors change in model and EMA; both normalization buffers
stay exact. The actual DINO backbone is hashed before/after each of three trainer
segments and remains bitwise unchanged and gradient-free. Optimizer restoration,
all manual/portable tensors including actual DINO and both full-photo predictions
match exactly. These are discarded engineering updates, not trained quality.

The CUDA fixture executes seven actual B16/native256/BF16 updates with workers0,
forced real Commons, paired and native domains. All94 initial EMA tensors and two
initial BF16 photo predictions match the mature parent. It verifies finite94/94/
92-state checkpoints,92 changed restoration tensors, exact normalization buffers
and actual DINO hashes/gradient-free flags. Portable FP16/BF16 predictions,
optimizer/RNG reconstruction and finite gradients through all92 trainable tensors
pass, including nonzero gradients in each restoration component and all three
head tensors. Sixty-four clean constant-field cases span four CFA patterns/four
colors/two conditioning profiles/two precisions, including negative/above-white
values, under the unchanged3e-7 bound. Peak CUDA allocation is **21.339GB**, not
total memory or throughput. No production/control input-match claim is made
because the seed and schedule differ from V66.

Separate CPU reads independently check both genuine saved fixtures, all92 moment
shapes, original recipe/source/data/RNG/logs and every logged LR against the10k
schedule. The review-tools preflight also passes the actual completed V65/V66
gates and exactly reproduces both entire published head-only boundaries. All36
retained V66 comparisons replay exactly;12 additional V66 self-comparisons have
zero differences/intervals. It checks50,264 primary cases without new inference.
Actual pending primary/hue/artifact owners reject before creating outputs.
The positive joint2000 gate can first execute when that real checkpoint exists;
no fabricated completed fixture is offered as proof.

Model source is unchanged from the previous543-passed/9-skipped CPU suite; that
suite is not claimed as rerun. The real joint CPU/CUDA checks above are new. Ruff
and diff whitespace checks pass for the review-tool changes.

The [first actual production checkpoint at500](results/raw-kernel-phase-joint-v67-first500-state.json)
also passes independent CPU inspection while the trainer continues: finite94
model/94 EMA/92 AdamW states, all92 restoration tensors changed, normalization
buffers exact, and original10k recipe/source/data/RNG/21 logged LRs verified.
Last LR is9.963796657738579e-5. This intermediate state audit performs no
inference and supplies no quality result; the first full review remains at2000.

## Executed training and serialized review

Training controller PID2848434/creation1792218667.87, child2848444/
1792218668.09, reports32,931,920 trainable parameters. At launch publication the
latest logged update is150 with finite loss/gradient. Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-workflow-v1.json`.

Primary controller PID2851586/creation1792218761.92 waits for that exact owner's
successful exit at2000/original10000. It independently audits the frozen state in
a separate CPU process before original known/unseen/full427, analytic, full GFX,
three cached cameras and selected CPU-color panels. Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-review-workflow-v2.json`.
The first waiting controller lacked the tool directory in its import path. It was
terminated before any child/evaluation; its immutable archive and retirement
receipt remain, and v2 resolves the archived imports in a fresh CPU process.
The training process and recipe were unchanged.

Statistics/hue controller PID2856800/creation1792218787.13 waits for actual primary
exit. It checks48 saved comparisons/12 classical witnesses against initialized
V66 and mature V60/V58/V43, then runs only the new checkpoint on the1,176 fixed
hue observations. Independent Torch64 checks cover7,056 fields/216 group scalars.
No old network bulk inference or legacy array merge. Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-statistics-hue-workflow-v1.json`.

Artifact controller PID2857122/creation1792218829.69 waits for actual statistics/
hue exit. It audits the joint94/94/92 boundary and original10k schedule,19 primary
PNGs/23 F32 arrays/two full RGB16 TIFFs. Four full-GFX native ROI checks must be
exact;18 three-camera rerenders retain the existing preview-only rounding bounds.
Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-joint-v67-artifact-workflow-v1.json`.

Verify current PID/creation/status before acting; do not duplicate or infer
completion from this launch snapshot. All owners and immutable plan guards were
independently verified at publication. Actual native viewing and quality decisions
are complete in the [first2k review](raw-kernel-phase-joint-v67-first2k-review.md). All four owners exited; PID records here are historical launch identities. The report must include two native exact-GT photo triplets plus
sky/building/foliage/fence GFX regions with accurate non-GT reference labels. Warm
RAF caches avoid the source drives; those scenes/siblings remain out of training.
Protected-final model scores remain unused. No promotion or continuation is
authorized by a queue result alone; assess full scores and native quality first.

The original10k budget has8,000 updates remaining. Verify an isolated continuation
from complete step2000 state, preserving this stopped run/log/source and its
immutable review, before further training. That continuation is not launched by
the first2k report; full final review remains required before promotion.

The [isolated continuation to the original10k endpoint](raw-kernel-phase-joint-v67-full10k.md)
subsequently passed actual full-size resume checks and launched. Its output
directory preserves all original2k evidence.
