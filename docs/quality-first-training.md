# Current quality training

**V120 Small is the general recommendation and quality-development parent.**
It keeps the V84-family pretrained DRUNet RGB trunk, physical noise/camera
conditioning and official frozen DINOv3 ConvNeXt-Small pyramid. Full427-photo,
camera/color, native-image and102MP RGB16 reviews are complete. Fine foliage,
weak texture, green mesh and dark-camera mottling remain unresolved.
[Current choices](current-model.md) · [Full results](v120-v121-primary.md).

Useful measured gains and native images determine the baseline; historical
promotion thresholds do not freeze the architecture. V117 Tiny has a slightly
higher photo mean; V114 Tiny has lower tested ADC maximum color bias. Broad
state-of-the-art quality, large real-camera superiority over RawNIND and100MP
within10s remain unproven. Quality takes priority over speed.

## Active quality questions

| Comparison | Fixed intervention | Present evidence |
| --- | --- | --- |
| [V124/V125 conditional mean](conditional-mean-training.md) |90,784 photos/20 regions; V120/seed67/20k; two noise views, mean-loss weights0/.25 | V12420k complete; V12520k running. [4k progress](v125-progress4000-quality.md) separates monitoring from native detail. Matched endpoints and repeated-noise bias pending |
| [V131/V132 spatial attention](raw-spatial-training.md) |90,781/29; V120/seed70/20k;22,664-parameter local branch off/on | V131 runs, V132 follows. [Control1k](v131-progress1000-quality.md) has tiny ordinary gains, shadow/faint regressions and no clear mesh recovery |
| [V133 photographic quota](reviewed-quota-training.md) | Same cohort/parent/seed/20k as V131;5% rather than50% reviewed sampling | CPU/CUDA16+2 pass; production/progress/full reviews queued after both spatial arms |
| [V134/V135 cleaned data and epochs](photo-epoch-training.md) |90,778/33; matched20k replacement/epoch sampling | All four CPU/CUDA16+2 checks pass; production/full reviews queued after V133's review |
| [V138 frozen-parent global branch](raw-global-only-training.md) |90,782/27;1k; freeze91 V120 tensors, train18 global tensors at LR1e−3 | CPU/CUDA16+2 pass; original1k/native/faint/GFX review queued after V125 completes |
| [V139 memory-only branch](raw-global-memory-only.md) | Same1k/data/parent/inputs as V138; remove direct local residual/MLP shortcut | CPU/CUDA16+2 pass;1k and102-input review queued after V138's review chain;510 saved predictions reused |

Jobs retain original sources, parents, data, budgets and dependency/resource
policies. Progress capture does not restart or stop a20k worker. Implementation
checks establish execution integrity; native/full endpoint comparisons establish
quality. The [saved monitor curves](v125-progress4000-quality.md) cover eight
photos/seven conditions/four CFAs and do not measure real mesh or replace full
photo/camera/color review.

## Current pipeline and prepared data

Current recipes use native256/B16, physical Poisson/read/ADC noise, all Bayer
layouts, camera/WB conditioning, geometry before final reduction and zero optical
PSF augmentation. Commons targets use4× binning → higher-resolution geometry
→ area2 reduction. Only the selected data domain is loaded/augmented.
[Augmentation, domain scheduling and batch evidence](training-pipeline.md).

The prepared future bank has **90,774 photos/36 reviewed regions**;
validation/test remain2,303/2,255. The [latest source inspection](v125-v131-source-review.md)
brings the ledger to2,043 IDs, retains all40 new sources and declines four
specialized weak annotations. It changes no manifest/catalogue bytes. Previous
exclusions and mixed white-plumage/leaf/feather additions remain preserved.
Prepared data and reader checks do not establish trained quality.
[Current source review](current-source-loss-review.md).

Corpus availability differs from actual visitation. The [20k schedule audit](training-source-schedule-coverage.md)
finds46.36% visitation at50% reviewed quota versus69.26% at5% on its fixed cohort.
The [optional epoch order](photographic-epoch-order.md) visits the whole prepared
cohort at the audited budget. V133 and V134/V135 test quality under these changes.
[Actual contrast coverage](training-target-contrast-coverage.md) distinguishes
weak material from flat backgrounds and source noise.

## Completed lessons and review practice

[V122/V123 frequency features](v122-v123-quality.md) give a small matched photo
gain with worse camera/color behavior and little weak-detail recovery.
[V136](v136-global-attention-quality.md) and [V137](v137-global-conditioned-quality.md)
give small mixed1k changes without clear new mesh recovery. The [trained-memory
diagnostic](global-memory-contribution.md) finds V137's local bypass dominates
its added feature offset on six contexts; V138/V139 test related interventions.
Band-loss, shadow-exposure, feature-loss and precision results retain their
strengths/failures in the [research index](research.md).

Improved-model reports include at least two native100% noisy/denoised/GT
triplets with identical coordinates/transforms and no resized crop pixels.
Record source/ROI, checkpoint hash, noise and exposure. Include the cached main
DSCF3879/3880 foliage/fence/building/sky scene and extra DSCF3842/DSCF3835 green
mesh with both JPEGs. Independent ISO100/AHD and native-binned references are
labeled accurately; they are not exact GT or real-reference PSNR targets.
Both pairs, JPEGs and siblings stay out of training.
[GFX gallery](gfx-qualitative.md) · [Fine mesh](gfx-green-mesh.md).

Keep README/current guides aligned with useful implementations and comparisons.
The [56-point version plot](performance-history.md) contains completed primary
endpoints; progress monitors stay separate. Historical launch decisions and the
exact previous guide are preserved in the [local-time diary](../diary/2026-10-27-20-54-44-v125-4k-quality-guide.md).
Original machine receipts, frozen plans, failures and checkpoints retain their
evidence. [Historical experiments](experiment-archive.md).

<a id="active-v104-cleaned-corpus-continuation"></a>
<a id="current-matched-comparison-v102v103"></a>
