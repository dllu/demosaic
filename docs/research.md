# Current method research

**[V120 Small](current-model.md) is the current general baseline.** It keeps
V84's pretrained DRUNet RGB restoration trunk with physical noise/camera
conditioning and official frozen DINOv3 ConvNeXt-Small spatial features.
Its completed full427 photo mean is37.04008dB, measured known/unseen-CFA means
54.31272/54.00872dB and tested ADC maximum55.52DN16.
[Primary results and native comparisons](v120-v121-primary.md).
V117 has a slightly higher single-view photo mean; V114 Tiny has lower tested
ADC maximum. Architectural choices follow their measured strengths rather than
historical promotion gates. Fine natural detail and real-camera blotches remain
unresolved; broad state-of-the-art quality is unproven.

## Current hypotheses and evidence

| Question | Evidence and current action |
| --- | --- |
| Can a frozen foundation encoder supply useful detail supervision? | [Completed V128 pilot](v128-feature-pilot-quality.md): the26-call gradient diagnostic passes, but weight.1 gives no useful gain at1,000 matched updates. Independent scores and all28 native boards are complete; the term stays off by default |
| Can RAW phase/frequency features preserve thin structures? | [Completed V122/V123 trial](v122-v123-quality.md): V122 slightly improves weak eight-pixel carrier response; V123 gains0.05493dB photo PSNR against it but lowers unseen-camera PSNR and greatly worsens the ADC tail. Weak natural detail/mesh remain soft; full numerical/selected native review is published |
| Can local attention use spatial repetition more effectively? | [Optional RAW spatial branch](raw-spatial-features.md) adds22,664 parameters and preserves constant features. The [V131/V13220k trial](raw-spatial-training.md) has four exact-recipe CPU/CUDA16+2 checks complete on90,781 photos/29 regions. Production waits for V125's admission; quality remains unmeasured |
| Can whole-tile matching preserve repeated weak detail? | [Completed V1361k](v136-global-attention-quality.md) has tiny mean gains, mixed local errors and no clear new mesh recovery. Its production gradients cover only updates1–16. A [saved-state/branch study and V137 follow-up](raw-global-conditioning.md) find almost uniform matching and test normalized attention with the same tensors. CPU/CUDA16+2 checks pass; matched1k training runs and restoration quality remains unmeasured |
| Does training precision limit faint detail? | [Completed V130](training-precision-pilot.md) changes only BF16→FP32 training against saved V129. Selected weak fur/grass/wood [faint-ADC bands](faint-adc-precision.md) improve slightly in gain/error while global PSNR falls0.01720dB. Native changes are subtle; noisy material and real mesh remain weak |
| Is weak detail lost through persistent conditional bias? | [Independent-noise diagnosis](conditional-noise-response.md) finds persistent faint fur/wood error after diagnostic multi-observation averaging. [V12414k progress](v124-progress14000.md) gives small noisy/shadow gains but worse faint ADC and no clear mesh recovery. Original20k control continues; [V125](conditional-mean-training.md) follows with added mean loss and a repeated-noise endpoint comparison |
| Does adding more realistic reviewed shadow detail help? | [Completed V126/V1271000-update pilot](reviewed-shadow-pilot-quality.md) finds no useful gain on its retained material/shadow/GFX support. Shadow policy stays off by default; the23-region reviewed bank remains available |
| Does fine-detail loss reweighting suffice? | [Completed V117/V11820k comparison](v117-v118-quality.md) finds lower weak natural-detail response and a worse ADC color tail with the normalized band term. Keep it off; improved local output-gradient alignment did not predict trained quality |
| Does encoder size alone fix weak contrast? | [Full Tiny/Small diagnosis](local-material-detail.md) finds nearly unchanged weakest-stratum gain on427 photos. Small's camera/detail tradeoffs remain useful; no size-only explanation is established |
| How much of the bigger corpus does a run visit? | [Full20k source audit](training-source-schedule-coverage.md) finds46.36% visitation at the spatial trial's50% reviewed quota versus69.26% at5%. [V133](reviewed-quota-training.md) now queues that quota-only20k comparison against V131; CPU/CUDA16+2 and independent saved-state checks pass. Quality remains unmeasured |

The latest [source inspection](current-source-loss-review.md) has1,923 unique
reviewed source IDs and a future34-region bank. Quality work uses zero optical PSF augmentation and
geometry before final downsampling, with reviewed material regions and corrected
paired-reference masks. [Training pipeline](training-pipeline.md) ·
[Actual target contrast coverage](training-target-contrast-coverage.md).
The optional [photographic epoch order](photographic-epoch-order.md) addresses
replacement-sampling omissions: actual reader paths confirm full prepared-corpus
visitation within20k, with unchanged family/domain choices. This is a data
coverage result; its trained reconstruction quality remains unmeasured.
The matched [V134/V135 training comparison](photo-epoch-training.md) now has all
four real CPU/CUDA16+2 checks complete and queues20k per arm on90778/33, followed
by complete numerical/native/GFX review with saved controls reused.
The [second V124 forty-source review](v124-second-source-review.md) retains38 and
withholds two display/artwork-dominated frames from a future90,778-source/33-region
cohort. It adds fine wing mesh and subtle pitted stone while preserving all31
prior region objects. Native annotations and actual saved full-context reader
draws distinguish intrinsic source contrast from augmentation. Existing training
inputs stay fixed: V131/V132 use90,781/29 and have full20k production queued;
their quality is unmeasured. The completed [V129](reviewed-detail-training-pilot.md)
27-region pilot has small mixed changes without clear large visible recovery.
The [new texture review](repetitive-material-source-review.md) adds one qualified
pale-feather context, preserving all33 earlier regions and the same90778 manifest.
Net-shop alias/moire and the grass-feather proposal's stronger contrast prevent
their specialized weak-detail admission. Existing trials and order policies stay fixed.

## Foundation features and the new objective

The official [DINOv3 implementation](https://github.com/facebookresearch/dinov3)
and [ConvNeXt-Small weights](https://huggingface.co/facebook/dinov3-convnext-small-pretrain-lvd1689m)
are locally available and hash-verified. Current recipes pin revision
`421020015aa4266363db803b6049a529999afb1e`, encoder SHA256
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
The [pyramid implementation](dino-convnext-pyramid.md) supplies frozen spatial
context alongside the direct restoration path; pretrained feature access is
working. The existing [DINOv3 license](../third_party/dinov3/LICENSE.md) applies.

The recent [GramSR paper](https://arxiv.org/abs/2604.25457) motivates testing
DINO feature supervision. Our [early spatial-MSE experiment](dino-feature-supervision.md)
uses corresponding feature locations, native camera-RGB rendering and the
existing frozen encoder instance. Its diagnostic and pilot distinguish measured
output gradients from trained quality; no GramSR reproduction is claimed.

The heldout review includes the main DSCF3879/3880 platform scene and the
additional DSCF3842 ISO6400 / **DSCF3835 ISO100 f/5.6** fine green mesh, with
camera JPEGs and independent low-noise references accurately labeled.
These private captures and siblings remain outside training.
[GFX comparisons](gfx-qualitative.md) · [Additional mesh](gfx-green-mesh.md).

## Comparator and implementation references

[RawNIND](rawnind-variants.md) remains an important released comparator;
its stronger variant still wins four of nine measured camera scene means.
The [nonlocal match/filter full review](nonlocal-reference-full-review.md)
and [other published-reference probes](experiment-archive.md) retain their
original finite support, source/license checks and input-transfer limitations.
They do not establish a universal ranking. Historical availability observations
are dated observations, not claims about today's upstream releases.

The [linear DNG/JPEG pipeline](dng-export.md) and hot-pixel repair are merged.
Complete102MP RGB16 output is verified; the100MP/10s target remains open.
Quality takes priority over optimization. [Current requirements](requirements.md).

The previous chronological design/access/release catalogue is preserved exactly
in the [timestamped diary](../diary/2026-10-27-00-42-21-dino-feature-supervision.md#exact-previous-research-page),
with its file hash and an independent byte copy. Frozen plans and original
machine receipts retain their bytes and explicitly labeled UTC times.
