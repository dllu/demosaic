# Direct CFA/native-phase conditioning: matched V66 trial

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

V66 completed its separate **1,000-update** head warmup after the
[failed V65 review](raw-kernel-warmup-v65-first1k-review.md). It tests one change:
give the reconstruction coefficients direct knowledge of the CFA pattern and
the output pixel's position in its 2×2 Bayer cell. The [completed review](raw-kernel-phase-v66-first1k-review.md) finds +1.69dB photo PSNR over V65, but substantial grain and a 6.14dB deficit versus V60: no promotion.
V43 was the reference for this experiment.

[Recipe](../configs/dino-convnext-raw-kernel-phase-warmup-b16-v66.yaml).
[Actual launch/source/data/startup](results/raw-kernel-phase-v66-launch.json).
[Executed CPU/CUDA checks](results/raw-kernel-phase-preflight.json).

## Architecture and controlled comparison

The existing 67 feature channels still predict324 coefficient logits. An optional
zero-initialized bank supplies one additional logit vector for each of four CFA
patterns and four native pixel positions. This adds5,184 parameters with the
default three supports, for **27,216 trainable parameters in three tensors**.
They change kernel coefficients before tanh; they never add an RGB offset.
The final output still combines same-color-centered RAW differences with
bilinear. Clean constant-color fields retain the original physical invariant.
Noise-dependent weights can still bias noisy fields or amplify noise.

The new model option is `raw_kernel_phase_conditioning: true`; it requires RAW
kernel reconstruction and defaults false. Disabled, the state keys and numerical
path remain compatible. Enabled, zero phase coefficients preserve initial output
and global RNG; no random draw is added by creating the bank. A nonpersistent
pattern table is reconstructed by the portable loader.

Only that flag, run path and experiment notes differ from V65's recipe. Both
initialize from the same mature V60 full 4k EMA with a fresh optimizer/EMA and a
zero head that starts at bilinear. Seed49, original 1,000 updates, LR2e-4/warmup50,
B16/native 256/BF16, original 40,170 Commons/native 128/paired32, all fractions,
wide8 palette, geometry/noise, workers4+2+2 and original 8× validation stay fixed.
The extra coefficient capacity is part of the intervention. The larger learning
rate that helped the toy diagnostic is not adopted simultaneously.

All 91 existing restoration tensors and their EMA remain frozen, along with the
actual DINO backbone. This is a new run from V60, not a V65 resume or joint stage.
The production controller requires all 41 logged input hashes/domain choices/LRs
to match completed V65 at the boundary. Source bundle:
`fc0297db08d659523fdcefe1ef0e7a4da12ae97f648e95b1579db65de93d268a`.

## Executed verification

Targeted RAW-head tests pass 35; the full CPU suite passes 543 with 9 CUDA-related
skips. The tests independently address all 16 CFA/native-phase categories,
preserve clean constants with arbitrary strong learned coefficients under BF16,
check global RNG and legacy state keys, and exercise trunk/head gradients,
optimizer selection, frozen EMA and checkpoint round trips.

The genuine-parent CPU fixture uses B1/native 64/FP32, workers0/forced smooth
Commons/val2. With the new flag disabled, eight saved state fields and every
numeric log/input hash exactly reproduce the previous32a source's four updates;
model_config is semantically equal with the added defaultFalse field. Loading
actual mature V65 reproduces both earlier full 256×256 CPU photo arrays bit for bit.

With phase conditioning enabled, seven updates match3+4 resumed updates in all
nine state fields and numeric logs. All seven matched-control inputs/domains/LRs
agree. All 94 model/94 EMA tensors and three AdamW states are finite, all 91 old
model/EMA tensors equal V60 exactly, and the three-state optimizer reconstructs
exactly. Portable/manual EMA tensors, including actual DINO, and two full-photo
FP32 predictions match exactly.

The actual B16/native 256/BF16 CUDA fixture then executes seven discarded updates
using workers0/forced real Commons/val2. All seven inputs/domains/LRs match the
original V65 CUDA fixture exactly. Finite94 model/94 EMA/three AdamW states,
unchanged91 parent tensors, complete optimizer/RNG reconstruction, exact portable
FP16/BF16 photo predictions and nonzero gradients through all three head tensors
pass. All other parameters are frozen and gradient-free. Sixty-four clean constant
fields cover four colors/four CFAs/two conditioning profiles/two precisions,
including negative/above-white numerical values, under the unchanged3e-7 bound.
No noise is added to these constant tests. Peak CUDA allocation is 16.709GB,
not total RAM or throughput. An independent CPU read checks the saved GPU state,
source and all 7 control observation hashes. These are engineering checks, not
quality, convergence or deterministic CUDA optimization after restart.

## Executed workflow and review

The completed production trainer reported 27,216 trainable parameters. Controller PID2517880,
creation1792216430.60; status:
`/mnt/external/demosaic/runs/raw-kernel-phase-warmup-v66-workflow-v1.json`.
Plan/logs:
`/mnt/external/demosaic/benchmarks/raw-kernel-phase-warmup-v66-workflow-v1/`.
Always verify actual PID/creation and child state before acting; never duplicate.

Primary evaluation waits for that exact owner's successful exit and all 41 matched
observations, controller PID2518363/creation1792216468.00. It uses the archived
fc0 model package and frozen panel operators for original known/unseen/full 427,
analytic, full GFX, three cached cameras and selected CPU colors. Warm RAW-cache
links avoid the originals. Status:
`/mnt/external/demosaic/runs/raw-kernel-phase-warmup-v66-review-workflow-v1.json`.

The [matched statistics/hue stage](results/raw-kernel-phase-v66-statistics-hue-queue.json)
ran after actual primary-owner exit, controller PID2527850,
creation1792216972.84. It includes V65 alongside retained V60/V58/V43, yielding
48 comparisons/twelve classical witnesses. The new-checkpoint grid uses the
original 1,176 observations, then 7,056 independent Torch64 fields and 216 group
scalars. Old reference networks are not rerun; legacy arrays are not merged into
the changed-source report.

The [artifact stage](results/raw-kernel-phase-v66-artifact-queue.json), controller
PID2528282/creation1792217056.81, waits for that exact statistics/hue owner to exit.
It checks the 94/94/three-state boundary, frozen 91 parent tensors, recipe/source/
data/RNG/logs and primary 19 PNGs/23 F32 arrays/two full RGB16 files. Four full-TIFF/
native-ROI comparisons must be exact; eighteen three-camera rerenders use the
unchanged historical preview-only bound. Actual native views and the quality
decision were completed afterward; neither queue promotes or continues a model.

[Executed CPU wiring checks](results/raw-kernel-phase-review-tools-CPU-preflight.json)
verify the actual completed V65 gate and published boundary unchanged, plus both
genuine seven-update phase CPU/GPU states and their full source snapshots.
All 50,264 V65 primary cases are checked; 36 published comparisons replay exactly,
and twelve additional V65 self-comparisons have zero differences and intervals.
These self-comparisons are engineering checks, not new quality scores. Pending
primary and actual live statistics-owner gates reject before output. Model code
remains unchanged from the 543-test fc0 package.

Matched V66−V65 statistics, full hue/state/artifact results and actual native
inspection are complete in the [performance review](raw-kernel-phase-v66-first1k-review.md). All four owners exited; PID records above are historical. The former 93/two-state gate is not used as proof
for this variant.
Reports need two native exact-GT photo triplets and all four standing GFX regions,
including foliage/fence, with non-GT real-reference labels. No automatic joint
stage, promotion, source/data substitution, fitted output or protected-final score.

After that completed review, a [separately declared V67 joint stage](raw-kernel-phase-joint-v67.md)
passed genuine CPU/CUDA checks and launched from V66 EMA. It has its own original
10k schedule and stops at2k for full review; this is not a V66 resume.
