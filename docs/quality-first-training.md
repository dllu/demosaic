# Current quality training

V119 is running a full 20,000-update continuation from **V115 Small** on the
cleaned Commons corpus and expanded paired data. Both discarded 16-step CPU/CUDA
checks passed before the fresh production run. Full numerical, independent and
native-image reviews are queued. Quality results are pending.
[Current recipe, execution and review](cleaned-diverse-small-training.md) ·
[Recipe file](../configs/quality-v115-cleaned-diverse-v119.yaml) ·
[Started-run evidence](results/v119-training-start-v1.json).

## Useful completed models

These are measured alternatives, with strengths and remaining weaknesses.
Their complete panels, native crops and RGB16 checks are published.

| Model | Architecture | Full-photo PSNR | Known / unseen measured-CFA PSNR | Useful strength and remaining weakness |
| --- | --- | ---: | ---: | --- |
| V114 | Frozen DINOv3 ConvNeXt-Tiny + pretrained DRUNet RGB trunk | 36.97973 dB | 54.28627 / 54.00290 dB | General camera/color balance; faint foliage and neon remain soft |
| V115 | Fitted DINOv3 ConvNeXt-Small + the same restoration family | 36.97700 dB | 54.32405 / 54.00417 dB | Stronger known-camera mean and eight-pixel weak response; higher tested color bias |
| V117 | V114 architecture, further 20k continuation | 37.04408 dB | 54.27303 / 53.97339 dB | Higher photo score, 421/427 source means up; slight camera regressions |

[Current selection and inference](current-model.md) ·
[Tiny/Small comparison](v114-v115-quality.md) ·
[V117 and the negative V118 band-loss result](v117-v118-quality.md).
V115 is the architectural parent for the running trial. Choosing V114 as the
current general inference option does not freeze the training architecture or
hide the useful Small and V117 gains. Study-specific promotion/significance
criteria do not replace direct comparison of overall metrics and actual images.

Broad weak natural-detail response is nearly unchanged between Tiny and Small
on the same 427 photos/5,124 cases. Their weakest ISO12800 gain is .36334/.36422,
despite Small's stronger eight-pixel analytic response. Both still smooth fine
foliage/neon and show dark-camera mottling. The stronger released RawNIND model
wins four of nine camera scene means. Broad real-photo superiority, state of
the art and 100MP within 10 seconds remain unmet goals.
[Local natural detail](local-material-detail.md) · [Real-photo comparisons](gfx-qualitative.md).

## Running recipe and data

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

Review the full endpoint after its declared budget. V119 has eight queued FP32
stages: full 427-photo/seven-condition/four-CFA, known/unseen cameras, weak
carriers, color, standing GFX, highlights and complete 101.996MP GFX output.
Independent NumPy64 checks operate on retained predictions/targets. Matched
comparisons reuse saved V115, V114 and V117 controls without new control inference.

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
