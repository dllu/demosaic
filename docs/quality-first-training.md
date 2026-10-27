# Current quality training

**V120 Small is the current general recommendation and quality-development
parent.** Its full numerical/native review and complete102MP RGB16 outputs
are verified. Fine photographic detail, green mesh and dark-field mottling remain
unresolved. [Current choices](current-model.md) · [Completed results](v120-v121-primary.md).

| Active comparison | Data and hypothesis | Current state |
| --- | --- | --- |
| [V124/V125 conditional mean](conditional-mean-training.md) |90,784 sources/twenty regions;16 unique targets and two noise views, mean-loss weights0/.25 | [V12414k progress](v124-progress14000.md): small noisy/shadow gains, faint ADC−.350dB, weak real detail unresolved. Original20k control continues; V125 follows |
| [V131/V132 spatial attention](raw-spatial-training.md) |90,781 sources/29 reviewed regions; same V120 parent, seed, inputs, single-view loss and20k schedule; spatial branch off/on | Four CPU/CUDA16+2 checks complete; production waits for V125's admission |
| [V133 reviewed quota](reviewed-quota-training.md) | Same90,781/29 and20k as V131,5% versus50% reviewed sampling | CPU/CUDA checks pass; early/full reviews queued; trained quality pending |
| [V134/V135 photo epochs](photo-epoch-training.md) | Cleaned90,778/33, same20k replacement/epoch comparison | Four CPU/CUDA checks pass; production and full reviews queued after V133's automated review |

The spatial trial's live early-review queue uses immutable step1,000 snapshots
within the original20k workers. Each gets102 retained material/shadow/faint-ADC
and real-scene inputs, with saved V120 controls reused. A separate full-endpoint
chain covers the full photo/camera/analytic panels, native images and RGB16 output.
Early snapshots do not stop training or become completed endpoints. Quality
and actual viewing are pending.

The [completed V122/V123 frequency trial](v122-v123-quality.md) gains0.05493dB
photo PSNR from joint training against adapter-only training, with lower unseen-
camera PSNR, a large ADC tail and little weak-detail recovery. The
[FP32 pilot](training-precision-pilot.md) gives small mixed faint-ADC changes.
Shadow/feature/data pilot outcomes and their native images remain linked from
the [current research page](research.md). New recipes use zero optical PSF and
geometry before final downsampling; existing trial inputs/budgets remain fixed.

## Useful completed models

These are measured alternatives, with strengths and remaining weaknesses.
Their complete panels, native crops and RGB16 checks are published.

| Model | Architecture | Full-photo PSNR | Known / unseen measured-CFA PSNR | Useful strength and remaining weakness |
| --- | --- | ---: | ---: | --- |
| V120 | DINOv3 ConvNeXt-Small + DRUNet, corrected paired32 continuation | 37.04008 dB | 54.31272 / 54.00872 dB | Current balanced recommendation, ADC maximum55.52DN16; matched-profile GFX review complete, fine foliage/neon/mesh remain weak |
| V121 | Same Small, cleaner90787/fourteen-region continuation | 37.04157 dB | 54.32184 / 53.98947 dB | Tiny photo change; ADC maximum1645.36DN16 and no clear fine-mesh gain |
| V114 | Frozen DINOv3 ConvNeXt-Tiny + pretrained DRUNet RGB trunk | 36.97973 dB | 54.28627 / 54.00290 dB | General camera/color balance; faint foliage and neon remain soft |
| V115 | Frozen DINOv3 ConvNeXt-Small + the same restoration family | 36.97700 dB | 54.32405 / 54.00417 dB | Stronger known-camera mean and eight-pixel weak response; higher tested color bias |
| V117 | V114 architecture, further 20k continuation | 37.04408 dB | 54.27303 / 53.97339 dB | Higher photo score, 421/427 source means up; slight camera regressions |
| V119 | V115 Small, cleaned90791/paired83 continuation | 37.03831 dB | 54.10063 / 54.00742 dB | Photo gain over V115; known-camera and ADC-color regressions, unresolved fine mesh |

[Current selection and inference](current-model.md) ·
[Tiny/Small comparison](v114-v115-quality.md) ·
[V117 and the negative V118 band-loss result](v117-v118-quality.md).
V115 is the fixed parent for completed V119–V123 trials.
The current V120 inference recommendation leaves those original comparisons
unchanged. Useful Small/V117/V114 tradeoffs remain explicit. Study-specific promotion/significance
criteria do not replace direct comparison of overall metrics and actual images.

Broad weak natural-detail response is nearly unchanged between Tiny and Small
on the same 427 photos/5,124 cases. Their weakest ISO12800 gain is .36334/.36422,
despite Small's stronger eight-pixel analytic response. Both still smooth fine
foliage/neon and show dark-camera mottling. The stronger released RawNIND model
wins four of nine camera scene means. Broad real-photo superiority, state of
the art and 100MP within 10 seconds remain unmet goals.
[Local natural detail](local-material-detail.md) · [Real-photo comparisons](gfx-qualitative.md).

## Completed recipe and prepared data

V119 retains V115's fitted encoder/laterals and restoration weights, with fresh
AdamW/EMA, seed 65, B16/native 256px/BF16, LR 1e-5 and 200 warmup steps. No feature
fit is repeated. Commons and native targets retain 4× binning → geometry → final
area2 downsampling, zero optical PSFs, photographic contrast attenuation and
legacy weak textures. Reconstruction epsilon is .0003, paired epsilon .0001,
fine-texture quota zero and band-loss weight zero.

The reviewed Commons cohort has **90,791 training sources**, with unchanged
2,303 validation and 2,255 test memberships. Source-preserving sampling keeps
unaffected source draws tied to the original 90,864-source reference. The six
reviewed fine-detail ROIs retain their 5% conditional-photo sampling probability.
High loss and metadata select review candidates; visual native/binned inspection
determines exclusions. Useful hard foliage, nets, textiles and fog stay eligible.
This is targeted quality review, not exhaustive manual inspection of the corpus.
[Corpus review](incoming-commons-quality.md) ·
[Actual cleaned-reader proof](results/cleaned90791-source-reader-preflight-v1.json).

Further native review retains 332 of 336 additional sources and prepares a
**90,787-source future cohort**, withholding two unreliable fine-texture photos
and two flat map/document layouts. Its coupled manifests and targeted actual
reader checks pass. It is selected for the queued V121 full run; its endpoint
quality effect remains unmeasured. V119 retains its original90,791 sources.
[Latest source decisions, native examples and reader scope](next-source-tail-review.md).

An optional [14-region material bank](weak-photographic-targets.md) preserves
the six original examples and adds eight measured weak photographic contexts,
including brick joints, plaster cracks, wavelets and sand ripples. Its actual
reader checks pass. It is prepared for the future cohort; its quality effect
is unmeasured; V121 selects it after passing implementation checks, while
V119/V120 retain their six-region recipes.

The paired set has **83 publisher IDs / 71 groups / 166 cases / 1,492 cached
crops**, preserving all four corrected legacy masks and every registered new
case. Camera probabilities remain Sony 75%, Canon 6D 12.5%, Nikon Z6 9.375% and
Nikon D40 3.125%, rather than increasing Sony simply because more of its groups
were added. The native clean 128-ID corpus is unchanged.
[Admission and sampler](paired-camera-sampling.md) ·
[Reference-mask review](paired-reference-quality.md).

Domain probabilities remain 50% Commons/procedural, 25% paired and 25% native.
Only the selected domain is loaded and augmented. Batch16 retains the measured
throughput/memory balance; quality takes priority over another speed sweep.
[Data order, sampling denominators and batch measurements](training-pipeline.md).
GFX3879/3880, their siblings and all protected captures stay outside training.
Originals are read-only; training and qualitative work use cached sources.

The new recipe combines data changes and extra optimization. Its comparison
to V115 does not isolate corpus size, camera weighting, masks or additional
training as separate causes. Full source/manifest/optimizer receipts and bounded
resource checks are recorded in the [V119 guide](cleaned-diverse-small-training.md).

## Review and documentation

Review the full endpoint after its declared budget. V119 completed eight FP32
stages: full 427-photo/seven-condition/four-CFA, known/unseen cameras, weak
carriers, color, standing GFX, highlights and complete 101.996MP GFX output.
Independent NumPy64 checks operate on retained predictions/targets. Matched
comparisons reuse saved V115, V114 and V117 controls without new control inference.
Its [11-capture native development comparison](native-camera-development.md)
also completed: clearer texture than RawNIND under added noise, small gains
over V115 and lower means than V117. The90,787-source/14-region bank is selected
for the queued V121 full run; [per-source loss tracing](source-loss-diagnostics.md)
is active in V120/V121. The matched paired32 control investigates the camera/color
regressions before treating the combined V119 recipe as the next baseline.

Improved-model reports include at least two native noisy/denoised/exact-GT
triplets with identical coordinates and display transforms, without resized
pixels. Record source/ROI, checkpoint hash, noise and display exposure. Include
all six GFX regions, especially foliage and chain-link fence. Its independent
ISO100 exposure and AHD camera references are approximate references, not exact
GT or pixelwise GFX scoring targets. Verify both RGB16 exports and native crops.
[Standing GFX test](gfx-qualitative.md) · [Performance history](performance-history.md).

Update the README and current guides when useful progress is established,
showing gains and adverse cases directly. Preserve machine receipts and original
experiment sources. The timestamped [diary](../diary/index.md) records historical
decisions; it does not constrain which useful architecture can be tried next.

## Completed evidence and retained preparations

These dedicated reports retain the historical comparisons and exact receipts.
They inform the current recipe; old launch/pending receipts are not live status.

| Study | Completed result or present status |
| --- | --- |
| [V117/V118](v117-v118-quality.md) | Extra-training control improves photo PSNR; added band term lowers weak natural response and worsens ADC tails; keep band off |
| [V116](v116-quality.md) | Fine weak-source profile plus corrected masks improves an eight-pixel carrier, with nearly unchanged broad weak detail and worse ADC tail |
| [V114/V115](v114-v115-quality.md) | Full fitted Tiny/Small comparison; useful camera/detail tradeoffs, no capacity-only causal claim |
| [V111/V112](loss-scale-training.md) | Smaller reconstruction epsilon supplies a useful quality continuation; V112 initialized the later Tiny/Small trials |
| [V104](v104-reviewed-corpus-quality.md) | Completed 20k cleaned-corpus continuation; all panels, native review and full RGB16 output complete |
| [V102/V103](v102-v103-quality-review.md) | Six versus 32 reviewed ROIs has a tiny matched photo effect; six retained |
| [V100/V101](v84-curated-quality-review.md) | Zero optical blur/weak-source/contrast/ROI package improves the V84 family; components not individually isolated |
| [V84/V85](native-data-original20k-review.md) | Extra native captures have little matched effect; the restoration family remains a useful baseline |
| [V93–V95](v43-curated-original20k-review.md) | Older ViT-S cleaned-data trials retain their original budgets and color/detail tradeoffs |
| [V96/V97](v95-flat-palette-quality-review.md), [V98/V99](v95-adc-training-quality-review.md) | Completed palette/ADC tradeoffs; no reason to freeze the baseline at V43 |
| [Earlier common-function Small preparation](convnext-small-capacity.md) | V109/V110 discarded checks complete; no production run; superseded as the active choice by fitted V115/V119 |

<a id="active-v104-cleaned-corpus-continuation"></a>
<a id="current-matched-comparison-v102v103"></a>

Older links to the V104 and V102/V103 sections resolve here. Their completed
reports above retain the full results, original recipes, source exposure and
receipts. Earlier unlaunched V107/V108/V109/V110 and V104-derived V113
preparations remain preserved, with no trained endpoint or live launch implied.
