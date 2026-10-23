# Controlled training test for faint detail

**V111 and V112 are queued continuations from the original V104 final 20k
EMA.** They keep the same architecture, data, initialization and budget, changing
only reconstruction Charbonnier epsilon: **.001 versus .0003**. Their training
waits for V104's owned evaluation and full-frame exports to finish. The [V104 material gains](heldout-detail.md) are
already published while its broader photo, camera and GFX evaluation continues.

The [fixed-output diagnostic](loss-smoothing-detail.md) found that smaller
epsilon strengthens gradients for faint low-noise detail, but increases the
total gradient more and reduces its alignment with the missing-detail band.
A trained comparison is needed to establish whether this helps restoration.
The .0003 arm tests a milder change than .0001. This test retains V104's learned
fusion gates; the separate [Tiny/Small preparation](convnext-small-capacity.md)
remains available for a later capacity comparison.

## Matched recipes

| Setting | V111 control | V112 smaller scale |
| --- | --- | --- |
| Reconstruction epsilon | .001, existing default | .0003 |
| Initial weights | Original V104 final 20k EMA, all 91 tensors unchanged | Same exact file |
| Frozen encoder | Official pinned DINOv3 ConvNeXt-Tiny | Same |
| Corpus | 90,864 reviewed Commons sources, native 128 / paired 32 | Same |
| Detail recipe | Zero optical PSFs, weak synthetic textures, photo contrast attenuation, original six ROIs at 5% conditional photo probability | Same |
| Schedule | Fresh AdamW/EMA, seed 62, 20,000 updates, B16/native256, BF16 | Same |
| Learning rate / warmup | 1e-5 / 200 updates | Same |

[V111 recipe](../configs/quality-v104-loss-scale-v111.yaml) ·
[V112 recipe](../configs/quality-v104-loss-scale-v112.yaml) ·
[Preparation, actual reader checks and discarded CPU/CUDA evidence](results/v104-loss-scale-prepared-v1.json) ·
[Actual live training/evaluation/export queues](results/v104-loss-scale-queued-v1.json).
Apart from output location, epsilon is the only arm difference. The original
parent is read-only at `/mnt/external/demosaic/models/v104-final20000.pt`, SHA256
`8a3a7d94f2b1465cbdddbeec201fb37a2f69b12c74f9298527a94e3a7bbf6300`.
No gate reset or backbone substitution is applied.

The setting changes ordinary camera-linear, rendered, spatial-gradient and
auxiliary Charbonnier penalties. Paired RAW retains its existing .0001 scale;
other sensor penalties retain their separate definitions. See the
[implemented setting and exact default replay](loss-smoothing-detail.md#configurable-training-scale).
Loss weights, clipping, optimizer and learning-rate schedule remain fixed.
Raw loss values across epsilon settings do not measure quality on a common scale.

## Actual checks and execution

Both recipes pass eight discarded CPU updates at native64/B1/FP32 and eight
CUDA updates at native256/B16/BF16. All 91 initial EMA tensors and the official
Tiny identity match. Each arm has finite model/EMA tensors and 89 finite Adam
states at step 8. Within each device setting, all eight actual input batches
and the first prediction/auxiliary output match exactly across loss scales.
The first loss and gradient change, confirming that the option reaches the
actual training objective. CUDA peak allocation is about 6.95GB; the checks
overlap V104 evaluation and do not measure throughput.

The diagnostic wrapper's first CUDA attempt lacked the main-entry guard needed
by spawned data-loader workers. Its failed log and source remain preserved;
the corrected wrapper runs CUDA in a new root and retains the successful CPU
evidence. The production trainer and recipes are unchanged.

The live execution controller adopts these successful checks after verifying
source and phase-configuration equivalence. It waits for the exact original
V104 export owner and child to exit successfully, then starts each 20k arm
freshly from the original V104 EMA. It does not repeat the smokes. Full matched
evaluation and complete 102MP RGB16 exports are queued afterward, with
[V102 as a separate fixed reference](../configs/quality-v104-loss-scale-reference-checkpoints-v1.json).
A [separate CPU material queue](results/v104-loss-scale-material-queued-v1.json)
will compare both final endpoints with V104 and V102 on the original 12 cached
observations, producing native noisy/restored/exact-GT triplets.
No production optimizer updates had started when the queue receipt was written.
Failures are preserved without automatic retry.

## Data and planned comparisons

The [completed source review](incoming-commons-quality.md) removes eight further
targets relative to V104: three degraded photographs and five printed atlas
reproductions. Four of the atlas sources were in the older V102 cohort. The
new cohort contains 2,391 eligible arrivals relative to V102, with unchanged
2,303 validation / 2,255 test records and protected real-capture exclusions.
Targets still use 4× binning, geometry augmentation and final area downsampling
by 2. Originals and prepared image pixels remain read-only.

The deterministic per-arm schedule contains 111,559 photographic examples from
62,367 unique sources, including 2,707 draws from 1,634 new eligible sources
and 5,657 reviewed-ROI examples. Twelve actual clean-reader checks cover six
new-source draws and all six ROIs; repeated native256 tensors match exactly
with finite output and unchanged Torch RNG. These are prospective exposure
counts and reader checks, separate from completed training.

Compare the original fixed final endpoints with each other and V104, retaining
V102 as a separately labeled reference. Use full photographic and measured-camera
panels, ADC color, weak texture, high-noise detail and the standing GFX scene.
Every improved-model report must include at least two native noisy/restored/GT
crop triplets with shared inputs and display transforms. GFX ISO100 remains
an independent qualitative reference rather than pixelwise GT. Record useful
gains and remaining weaknesses directly, then update the current guides and
README comparisons.

The V111/V112 difference tests the loss scale under one matched recipe and
seed. A gain over V104 also changes training duration, seed and corpus, so it
would not isolate the cleaning effect. Discarded eight-update checks establish
implementation behavior, without establishing restored quality or throughput.
Original V104 evaluation/export queues and earlier capacity evidence remain
unchanged.
