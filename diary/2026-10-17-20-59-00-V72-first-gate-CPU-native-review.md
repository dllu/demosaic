# V72 first gate and selected CPU native review

The previous goal turn made progress by freezing and starting the full FP32
quality-review queue. This turn revalidated the exact live training/review
owners, then confirmed V72 no-DINO finished2,000 optimizer/8,000 data steps /
32,000 examples. Worker2340415/1792293416.11 exited successfully and its
immutable checkpoint is
`8d67375e2169adb88f7dcdafd253e23642eb0d87b1dc2d79416cb0f22320416a`.
DINO continuation2404322/1792295586.28 is now live. The matched GPU review
still waits for both completed boundaries and controller/final-child exit.

Used available CPU time for actual trained-quality evidence. The new helper
independently validates both V72 prefix/final model/EMA/852Adam/RNG state,
source bundle, original schedule, all82 logged mixed groups and82 overlapping
old V71 source/noise hashes before inference. CPU2threads/nice10, CUDA hidden,
no original/cold-drive access or active recipe/queue mutation.

Compared V72 against originalRAW8k/40k, V43/V63 and both RawNIND gain adapters
on two existing fixed exact-target CPU observations and all four GFX contexts.
Prepared common32-aligned512-pixel GFX windows from the already-cached full
normalized RAW. All four standing160×160 raw sample ROIs and their Malvar
values match the old contexts bitwise. Sensor/reference crops stay fixed.

All42 F32 predictions/native triplets finish; actual CPU owner exits. Both
native boards, representing all42 triplets, and four new individual V72
triplets are viewed. Independent saved readback verifies all42 float hashes/
shapes/finiteness and exact denoised previews,12 common noisy/reference panels
and54 copied native-board cells. No crop resizing or GPU initialization.
The rendering operator is reused, not an independent metric-definition audit.

Selected synthetic sRGB PSNR is28.79973/26.00101 for V72 against
28.29771/25.49915 for originalRAW8k at equal32,000 examples. This~.50dB gain
on two preselected single-condition inputs is not a population result or a
causal unit/batch/precision ablation. V72 still has strong grain, is worse
than oldRAW40k and far behind mature V43/V63 here; no clear foliage/fence
detail gain. RawNIND keeps wavy fence/building artifacts. No promotion or
training extension follows this selected review.

Public review and two exact-GT triplets plus foliage/fence triplets:
`docs/packed-isotropic-mixed16-V72-CPU-preview.md`.
Complete receipt:
`docs/results/packed-isotropic-mixed16-V72-CPU-preview-v1.json`.
Private42-case outputs/readback:
`/mnt/external/demosaic/evaluation/packed-isotropic-mixed16-no-dino-first32000-CPU-preview-v1/`.
28 boundary/reporting CPU tests and Ruff pass. Full matched quality, SOTA,
large real-photo superiority and100MP/10s remain unproven/unmet; goal stays active.
