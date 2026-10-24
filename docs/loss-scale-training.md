# Controlled training test for faint detail

**V111 and V112 completed their original20k endpoints from the same V104 EMA.**
Full matched GPU evaluation is running; the four-model CPU material report has
finished computation and awaits actual native review.
V111's [early material/GFX review](v111-early-quality.md)
improves all twelve material cases over V104, with small real-photo changes.
V111's complete camera panels change −.01336/+.02006dB known/unseen versus V104;
V111's complete analytic grids show improved coarse carriers/high-noise color
and a worse ADC flat-bias tail. Full-photo and matched V112 results remain pending.
Both keep the same architecture, data, initialization and budget, changing
only reconstruction Charbonnier epsilon: **.001 versus .0003**. The trial
started after V104's owned evaluation and full-frame exports finished.
[Completed V104 strengths and tradeoffs](v104-reviewed-corpus-quality.md) and
[material gains](heldout-detail.md) remain separate from this new hypothesis.

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
[Actual production launch, corrected handoff and live queues](results/v104-loss-scale-training-started-v2.json).
Apart from output location, epsilon is the only arm difference. The original
parent is read-only at `/mnt/external/demosaic/models/v104-final20000.pt`, SHA256
`8a3a7d94f2b1465cbdddbeec201fb37a2f69b12c74f9298527a94e3a7bbf6300`.
No gate reset or backbone substitution is applied.

The adopted V112 final checkpoint is read-only at
`/mnt/external/demosaic/models/v112-final20000.pt`, SHA256
`21c3cca8370df21e3412f9ccbf441c35afcfad8fd03174c7727f4f88874783b1`.
Its original trainer/controller have exited. All 91 model/EMA tensors and 89
Adam states at step20000 are finite, and all 801 logged input/domain/LR rows
match V111. [Endpoint, exact canonical copy and comparison handoff](results/v112-original20000-training-boundary-v1.json).
This establishes training completion; image-quality conclusions await the
matched reports and native/full-frame review.

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
source and phase-configuration equivalence. It verified the exact original
V104 export owner and child had exited successfully, then started V111
freshly from the original V104 EMA. Its first logged loss, gradient and input
hash reproduce the CUDA preflight exactly. It does not repeat the smokes. Full matched
evaluation and complete 102MP RGB16 exports are queued afterward, with
[V102 as a separate fixed reference](../configs/quality-v104-loss-scale-reference-checkpoints-v1.json).
A [separate CPU material queue](results/v104-loss-scale-training-started-v2.json)
has computed both final endpoints with V104 and V102 on the original 12 cached
observations, producing native noisy/restored/exact-GT triplets awaiting review.
V112 started after V111's fixed endpoint and original worker exit. Its first
input/loss/gradient replay its CUDA preflight; all 801 logged input/domain/LR
rows match V111 through the original20k endpoint. This verifies execution;
quality is assessed with image metrics and native comparisons.

An additional [early CPU material queue](results/v111-final20000-early-material-queued-v1.json)
finished V111's fixed final20k endpoint after verifying the original worker's
exit and controller adoption. It used the same twelve cached observations,
saved unquantized predictions/native160 triplets and added no V104 inference.
The [completed early report](v111-early-quality.md) shows +.254/.100/.019dB
ADC-only/ISO100/ISO12800 and all twelve PSNR/SSIM/chroma/gradient cases improving.
Six GFX context comparisons look close to V104. This supplementary review is
separate from the unchanged full matched evaluation and later four-model
material queue; no intermediate checkpoint was selected.

A supplementary [completed V111 CPU diagnostic run](results/v111-texture-color-complete-v1.json)
covers all 448 original weak-texture/neutral-flat and 1,176 flat-color cases.
The independent audit passes and all 40 native cells were actually viewed.
High-noise mean/max flat bias improves to 17.85/91.89 DN16; ADC bias worsens to
27.64/2,142.98 DN16. Fine 8-pixel carrier response remains weak despite a gain.
The [combined report](v111-early-quality.md#complete-weak-texture-and-flat-color-panels)
shows the original selections and V111's new worst ADC field. This adds no
training or CUDA inference and leaves the original matched queues unchanged.

The first queue stopped before any optimizer update because its controller
looked for a child field omitted from terminal export status. A new controller
binds the immutable export-result owner instead. Failed queues and source bytes
remain preserved; current training and reporting use separate v2 roots. The
frozen recipe definitions retain their bytes, with controller-resolved outputs
under `/mnt/external/demosaic/v104-loss-scale-20261023-v2/train/{V111,V112}/`.
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
with finite output and unchanged Torch RNG. These are reconstructed exposure
counts and reader checks. Both completed their declared schedules; the counts
do not independently verify every unlogged fetch.

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
