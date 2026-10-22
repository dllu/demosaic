# Bounded RAW-kernel head warmup

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

V65 completed its original **1,000-update** warmup and full quality review.
The [completed report](raw-kernel-warmup-v65-first1k-review.md) finds poor denoising;
there is no promotion or joint continuation. The launch history follows. It starts from V60 full4k EMA and freezes
all 91 existing restoration tensors, including DINO projections/gates, while
learning 22,032 coefficient parameters. Actual DINO stays frozen. The new head
starts at bilinear quality: this is a new stage with fresh AdamW/EMA, rather
than a continuation preserving parent-quality output. V43 was the reference for this experiment.

[Recipe](../configs/dino-convnext-raw-kernel-warmup-b16-v65.yaml).
[Actual launch, archived source/config/data and startup](results/raw-kernel-warmup-v65-launch.json).
[Reconstruction rule and limits](raw-kernel-reconstruction.md).

The [completed data review](long-commons-v63-v64-first4k-review.md) found no clear
native detail gain from extra Commons membership at its first 4,000 boundary.
This experiment changes reconstruction while keeping original 40,170 Commons/
native128/paired32 membership, source fractions, wide8 palette, geometry/PSF,
noise/ADC and original 8× validation fixed. Head warmup uses seed49,
LR2e-4/warmup50, B16/native256/BF16, workers4+2+2 and an original 1,000-update
budget. Its new initialization/budget prevents treating parent comparisons as
isolated architecture evidence.

The [actual head-only CUDA fixture and independent CPU audit](results/raw-kernel-warmup-CUDA-preflight.json)
pass before launch. Seven discarded production-size updates cover all three
domains with forced real Commons/workers0/val2. All 91 old model/EMA tensors
remain bit-for-bit equal to V60; only two new head tensors change. All 93 model/
93 EMA tensors and two AdamW states are finite. Saved optimizer/RNG reconstruction
and two portable/manual EMA FP16 photo predictions match exactly. A native256/
B1/BF16 probe has finite nonzero head weight/bias gradients .06141/.03629,
with all other parameters frozen and gradient-free. Peak CUDA allocation is
16.709 GB, not total unified RAM or production throughput. Original import and
independent-audit helper failures are retained with their corrections; no
training checks or tolerances changed.

Production reports exactly 22,032 trainable parameters. Controller PID2133207,
creation1792213815.95, imports archived32a model code, with frozen source/recipe/
data guards. Status:
`/mnt/external/demosaic/runs/raw-kernel-warmup-v65-workflow-v1.json`.
Logs/plan:
`/mnt/external/demosaic/benchmarks/raw-kernel-warmup-v65-workflow-v1/`.
Inspect actual PID/creation and child state before acting; never duplicate it.

Primary review completed after that exact owner's successful exit,
PID2134771/creation1792213912.51. It checks the complete step1000 state and
frozen parent tensors, then evaluates original known/unseen, 427-photo/procedural,
analytic, full GFX, three cached cameras and selected CPU colors. The working
directory contains the actual archived model code, preventing provenance from
capturing later root edits. Warm RAW-cache links avoid cold originals. Status:
`/mnt/external/demosaic/runs/raw-kernel-warmup-v65-review-workflow-v1.json`.

Independent statistics, the full fixed hue grid, artifact/state checks and all
26 native views have completed; see the performance report above. The performance report must include at least two
native noisy/denoised/exact-GT photo triplets and all four DSCF3879/3880 regions,
including foliage/fence, with accurate non-GT labels. There is no automatic joint
stage or promotion. A later joint stage must initialize a new run from warmup
EMA with fresh optimizer/EMA and its own declared budget. No protected-final
score, output fitting, convergence, noisy-field unbiasedness or SOTA claim follows.
