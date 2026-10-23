# Project goals and current evidence

**V101 is the current development checkpoint in V84's architectural family.**
Its full-photo result is 36.50347 dB, +.06351dB over V84 and about 1.60 dB above V43.
Camera CFA means remain close to V84, with high-noise fine-detail loss still open.
[Current choices](current-model.md) and the [README](../README.md) show useful
progress; individual study gates do not freeze those recommendations.

The broader objective in [PROMPT](../PROMPT.md) remains active. Quality has
priority over speed. The current [GFX gallery](gfx-qualitative.md) includes
V84/V100/V101 on all six fixed regions; their real-capture differences remain small.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint demosaicing and denoising | V101:36.50347dB on full427; close measured-CFA means and cleaner geometry than RawNIND in current native comparisons | Improve fine texture, color tails and real-photo results; make strong benchmark claims only when their comparisons are complete |
| Much better real-photo quality than RawNIND | Current GFX comparisons show more coherent mesh/rails and less grain with the learned models | Broaden actual scene/camera comparisons and recover more foliage/weak detail |
| 16-bit and practical full-resolution output | Shared inference/export pipeline has produced verified101.996MP RGB16 TIFFs; V84's exact EMA loads through current code | Keep full-frame quality/precision/timing measurements specific to the selected checkpoint |
| 100MP within10s on GB10 | Full-frame timing/export infrastructure exists; the target is still open | Measure and optimize the selected quality model after quality work |
| Modern DINOv3 method | V84 uses the official pinned ConvNeXt-Tiny pyramid with pretrained DRUNet RGB restoration | Continue improvements from this strong family and assess other approaches when useful |
| Free, diverse targets and aggressive binning |88,484 curated Commons training sources;4×→geometry→area2; native/paired targets and recorded attribution | Train and assess the current V84 continuations; expand useful real fine-detail coverage |
| Physical noise/exposure and camera handling | Poisson/read noise, negative black-subtracted values, Bayer phases, clipping and WB/matrix conditioning are implemented | Continue testing shadows, saturated lights, color and low-noise behavior |
| Reliable training and resource use | Source/manifest snapshots, restart checks, bounded jobs and actual CPU/CUDA operation | Monitor current runs and retain failures/results accurately |
| Protected originals and evaluation scenes | Originals read-only; cached GFX3879/3880 and siblings excluded from training | Preserve those boundaries in new data recipes |
| Current documentation and reproducibility | Native crops with source/ROI/weights/noise/display metadata; local-time diary; Git history | Update README/current guides and comparisons when good versions appear |

## Active quality work

[V100/V101](quality-first-training.md) use V84's architecture and exact final EMA,
curated88,484 Commons, original native128/paired32 and its broad flat palette.
The matched recipe comparison tests original augmentation against zero optical
PSFs, weak synthetic textures, photographic contrast attenuation and reviewed
ROI sampling. Both budgets are10,000 updates; short CPU/CUDA smokes are discarded.
Both fixed endpoints and all seven evaluation panels have completed. V101
reaches 36.50347 dB on full427 (+.06351 dB over V84), with camera CFA means close
to V84 and remaining real fine-detail loss. It is the next quality checkpoint.
[Completed primary results](v84-curated-quality-review.md). Full-frame exports
are complete and independently verified; status and artifact locations are in the training guide.

Actual source-quality review covers 570 sources: 539 retained/31 withheld, after
a complete loss/proxy scan of88,508 training sources. The active runs use the
earlier 24 exclusions; seven newer exclusions and a 32-region detail catalogue are
applied in the separate 88,477-source V102/V103 cohort. Hard or high-loss material
is not automatically bad data. [Native source examples](corpus-source-review.md)
show the decisions; protected holdouts and series stay fixed.

V101's completed continuation improves PSNR/SSIM on all12 selected cases against
V84 and V100 in the [natural-detail gallery](heldout-detail.md), with small visible
gains and remaining high-noise smoothing. Current
[Q2/Sony/GFX50R comparisons](cross-camera-qualitative.md) show V84/V100 beside
V43 and RawNIND. The [completed three-model camera comparison](real-camera-quality.md)
shows V101 CFA means close to V84, with auxiliary RGB tradeoffs. All seven
quality panels and full-frame GFX exports have finished. V102/V103 now train
from V101 with six versus 32 reviewed regions on the88,477-source cohort.
The [16-scene paired test reserve](paired-reserved-test.md) is prepared and
validated, with no model inference or scores; it remains outside model selection.

The [experiment index](experiments.md) and [PSNR history](performance-history.md)
retain earlier gains and tradeoffs. For example, V95 improves a tested weak
carrier, while V98/V99 improve ADC color but retain positive-noise color/detail
issues. These observations inform the current recipe without making V43 the
default again.

## Evidence for the full objective

Assess useful trained versions against the current baseline and strong
comparators on the fixed photographic/camera panels and actual native images.
Retain source/scene intervals and adverse cases. Each reported improved model
needs at least two native noisy/restored/GT crop triplets with matching
coordinates/transforms, checkpoint hash, conditioning and display exposure.
Real AHD/separate ISO100 references remain nonexact and are not pixelwise GT.

Show credible improvements and update current examples as they appear. Claims
such as state-of-the-art quality, broad real-camera superiority or a particular
100MP runtime need evidence covering those claims; they are not prerequisites
for documenting an improved implementation or choosing a better baseline.

The [diary](../diary/index.md) and [historical evidence log](requirements-archive.md)
retain prior decisions. Existing machine receipts preserve original bytes and
study-specific decisions, while current prose reflects today's implementation.
