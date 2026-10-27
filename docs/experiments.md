# Experiment index

**V120 Small is the current general recommendation in V84's architectural family.**
Its photo/known/unseen means are37.04008/54.31272/54.00872dB, with ADC maximum55.52DN16.
[Completed primary/local/native results](v120-v121-primary.md) document the gains,
remaining detail loss and completed matched-profile main-GFX comparison.
V114 remains a useful Tiny alternative; V115 has higher known-camera quality
and V117 a slightly higher photo mean. In the earlier V114/V115 pair, Tiny has
slightly higher photo PSNR and lower color bias.
[Completed panels, native comparisons and full exports](v114-v115-quality.md).
Fine foliage/neon and dark-camera mottling remain weak. [V116 has completed full review](v116-quality.md)
to test fine weak sources and reviewed reference masks against matched V114;
eight-pixel carrier gain rises, but broad weak-material gain is unchanged and ADC tails worsen.
The [completed V117/V118 loss pair](v117-v118-quality.md) gives V117 a useful
single-view photo mean of37.04408dB, with slightly lower camera means and higher
ADC bias than V114. V118's band term lowers weak natural response and raises
worst ADC bias to843.05DN16. All numerical/native/full-frame review is complete;
the term stays off for further quality work.
The [V119 trial](cleaned-diverse-small-training.md) continued from
final V115 Small on90,791 cleaned Commons sources and the corrected83-ID paired
set with the original camera proportions. Its [complete review](v119-quality.md)
finds a+.06131dB photographic gain over V115, −.22342dB known-camera change,
and a large ADC color tail. Weak natural detail and real fine mesh remain soft.
All endpoint, independent, native and full-output checks are complete. The
[native development comparison](native-camera-development.md) also documents
the joint models' clearer detail than RawNIND on11 binned camera captures.

The [V120/V121 follow-up](paired32-weak-detail-training.md) keeps V115 Small,
restores corrected paired32 at V119's90791/six-region data, then tests the
reviewed90787/fourteen-region intervention. CPU/CUDA checks pass for both;
V120/V121 completed20,000 updates and independent numerical audits. The
[early V120 mesh review](gfx-green-mesh.md#v120-after-correcting-the-paired-data-mix)
shows no clear lattice-recovery gain over V115/V119, and V121's mesh remains
similarly weak. Saved/local-detail and selected native review is complete. The [report repair](endpoint-quality-review.md#material-selection-and-gfx-conditioning)
preserves material-pair differences and explicitly labels the older/new
main-GFX noise profiles. The additional
[fixed-Haar full-frame comparison](v120-v121-primary.md#matched-profile-full-frame-gfx)
now matches older inputs exactly, with subtle changes and continued detail loss.
[Completed primary means and native triplets](v120-v121-primary.md) show V120's
camera/color recovery and V121's remaining ADC tail.
The [V120/V121 camera-linear extension](native-camera-development.md#v120v121-extension)
adds480 new predictions on the frozen11-capture development set and reuses960
controls. V120 gains modestly over V115 and retains much finer texture than
RawNIND; V117 retains higher condition means and V121's changes are tiny.

The [V124/V125 mean-loss trial](conditional-mean-training.md) uses V120's
architecture and parent on the cleaned90,784-source/twenty-region corpus.
All four CPU/CUDA16+2 checks pass; V124's original20k control is complete and
V125's original20k training is running. Both arms use16 unique targets and32 simulated observations,
with mean-loss weights0/.25. [V12414k progress](v124-progress14000.md) finds
noisy/shadow PSNR+.008–.033dB, faint ADC−.350dB and no clear fine-mesh recovery.
Full endpoint and repeated-noise mean-loss comparison remain pending.

The [completed V136 global-attention pilot](v136-global-attention-quality.md)
matches all1,000 clean/noisy batches to saved V129 and adds exactly102 quality
forwards. Ordinary/shadow/faint means rise slightly over V129, but local detail
changes are mixed and no clear new fine-mesh recovery is visible. Native
triplets, both corrected GFX scenes and independent score/pixel audits are
published. V120 remains the general recommendation; no20k global run is queued.

The [completed V137 conditioned-global follow-up](v137-global-conditioned-quality.md)
normalizes matching after diagnosing almost uniform V136 attention. It shows
stronger query/key adaptation and faint ADC+.0334dB over V136, with ordinary/
shadows−.0005–.0044dB and mixed local detail. All102 new predictions, independent
audits and38 actual native views are complete. No clear new fine-mesh recovery
is visible; V120 remains the general recommendation. [Operator/mechanism](raw-global-conditioning.md).

The [V138 branch-only pilot](raw-global-only-training.md) freezes all91 V120
model/EMA tensors and trains the same18 global tensors at LR1e−3. Genuine
CPU/CUDA16+2 checks and independent state/input verification pass. Its original
1k production and102-input native/GFX review are queued after V125 completes.
The combined freezing/LR intervention has no measured quality result yet.

The [V1239k frequency-feature midpoint](v123-midpoint-quality.md) now includes
16 material predictions and six GFX contexts, reusing47 saved controls. Selected
PSNR changes are tiny, and fine mesh/foliage remains weak. Its
[completed20k endpoint review](v122-v123-quality.md) now supersedes that progress
snapshot, with a small joint-arm photo gain and camera/color tradeoffs.

The [current V114 eight-view pilot](v114-eight-view.md) improves all12 fixed
material cases and both selected camera crops, with a small selected color-bias
tradeoff; independent/native review is complete and full panels/frame remain
unmeasured. The earlier [V112 eight-view pilot](v112-eight-view.md) retains its explicit
weights and unmeasured full-panel/frame scope.

[Current model choices and images](current-model.md) ·
[Current quality training](quality-first-training.md) ·
[PSNR history and full table](performance-history.md) ·
[GFX comparisons](gfx-qualitative.md) ·
[Experiment archive](experiment-archive.md).

![PSNR history](images/version-PSNR-history.png)

The figure describes completed checkpoints with different architectures,
initializers, data and training horizons. It shows real progress; use the linked
matched studies when attributing a gain to a particular change.

## What the main experiment families established

| Family | Main finding | Evidence |
| --- | --- | --- |
| Geometry and original V43 | Geometry/PSF before the final 2× reduction helped the matched photo test. Diverse native targets and the full-resolution RGB/DINOv3 ViT-S model established the earlier ViT-S baseline | [V34/V36](geometry-corpus-v34-v36-review.md), [V43 step 2000](native-corpus-2k-review.md) |
| Larger Commons corpus and longer training | Established the stronger ConvNeXt-pyramid family; the isolated corpus expansion adds a modest photographic gain | [V63/V64 original20k](long-commons-v63-v64-original20k-review.md) |
| Color coordinates and supervision | Normalization, objective and camera-supervision changes produced tradeoffs | [V68/V69](normalization-v68-v69-original4k-review.md), [V74/V75](reconstruction-objective-first1k-review.md), [V76/V77](camera-supervision-first1k-review.md) |
| Compact RAW-native architecture | The completed mixed-batch experiment remains far below the mature RGB models on primary panels | [V72/V73](packed-isotropic-mixed16-quarter-review.md) |
| Directional, interval and bank heads | Several heads improve photographic means, with camera/detail tradeoffs; the simpler V84 family is stronger overall in the completed primary scores | [V78/V79](directional-interval-original4k-review.md), [V80/V81](directional-bank-original4k-review.md), [V82/V83](bank-detachment-original4k-review.md) |
| Native data and larger context | V84/V85 establish the36.44dB architectural reference continued by V101. The extra native captures have little matched effect; larger context is a separate small-effect comparison | [V84/V85](native-data-original20k-review.md), [V86/V87](training-context-original4k-review.md) |
| Spectral and late RGB refinement | Small matched mean gains or protected common weights did not fix weak detail; head-only V92 regressed | [V88/V89](spectral-original4k-review.md), [V90/V91](late-rgb-original4k-review.md), [V92](late-rgb-head-only-original4k-review.md) |
| ADC-only inference | With unchanged V104 weights, replacing only valid measured sites gains .2885 dB rendered PSNR across all 427 sources/all 1,708 CFA cases. Local chroma/SSIM regressions and a flat-color tail remain; positive-noise profiles bypass it | [Complete site-consistency comparison, actual export and native crops](adc-consistency.md) |
| Eight-view inference | Full427 photo PSNR37.04376dB; all 427 source means and4/4 known,5/5 unseen scene means improve over V104 single. ADC tail420.90DN16 remains worse than V112, with fine-detail/blotch weaknesses. Costs eight evaluations per tile | [Full panels, native examples and independent audit](dihedral-quality.md), [complete-frame comparison](dihedral-fullframe.md) |
| Fixed Tiny/Small output mean | Equal V115/V117 mean gives photo37.02408dB and camera54.31387/54.00195dB: an intermediate tradeoff, with no clear native GFX detail gain. All14,190 numerical cases reuse saved predictions | [Scores, two exact-GT triplets and six native GFX regions](fixed-tiny-small-mean.md) |

Each complete quality review retains source/checkpoint identities, native
noisy/restored/reference crops and explicit real-reference limitations. The
[chronological archive](experiment-archive.md) preserves the longer record,
including early versions, negative studies and engineering details.

## Data and current quality work

V100/V101 completed10k continuations from V84 on the curated88,484-source Commons cohort. One
retains V84's augmentation; the other tests zero optical PSFs, weak synthetic
textures, photographic contrast attenuation and reviewed fine-detail ROIs.
The architecture, broad flat palette, native128 and paired32 targets stay fixed.
See the [recipes, execution status and evaluation approach](quality-first-training.md).
V101 reaches **36.50347dB** on full 427, +.06351dB over V84, improving 418/427
source means and all seven condition means. Known/unseen CFA means remain close
to V84. The [completed primary report](v84-curated-quality-review.md) and
[current native gallery](heldout-detail.md) show gains and remaining smoothing.
V102/V103 completed their20k six/32-region comparison on88,477 sources. All seven
evaluation panels and full-frame exports finished. V102 improves425/427 source
means over V101; the six/32 ROI effect is small and mixed across diagnostics.
[Completed current results](v102-v103-quality-review.md). V104 completed 20k
from V102 on 90,872 sources with 2,395 eligible additions. It improves PSNR,
SSIM and gradient error in all 12 selected material cases; [native comparisons](heldout-detail.md)
are current; all seven evaluation panels and full-frame exports are complete.
[Source review and native examples](incoming-commons-quality.md).
The [complete paired training-reference audit](paired-reference-quality.md)
also prepares a narrow opt-in mask revision for two recurring red-speck
references, preserving useful flagged texture and the active data bindings.
The [completed V111/V112 loss-scale comparison](loss-scale-training.md)
uses the cleaned90,864-source corpus and original V104 EMA/gates. Both add about
.10dB on full427; V112 improves camera/color over V111 and supplies the
parent of current V114. The [primary report](v111-v112-primary-quality.md) and
[complete review](v112-quality.md) show native strengths and remaining limits.
The [completed Small transfer](small-feature-transfer.md) now uses V112 teacher
targets and cached training features. Photo means remain close, while two dark
camera crops lose .20–.32dB. Matched Tiny V114 / fitted Small V115 passed eight
actual CPU/CUDA updates each; [both have completed 20,000 updates](small-aligned-training.md).
[Complete quality review](v114-v115-quality.md) now selects Tiny for general
photo/color balance while documenting Small's known-camera/eight-pixel gains. The old idle V113 plan and evidence remain preserved.
Their [endpoint evaluation queue](quality-prediction-archive.md) retains exact
targets and native predictions across all numerical panels, with standing GFX
contexts and complete-frame exports; existing controls are reused.

The [clean-target frequency audit](fine-weak-texture-coverage.md) finds a narrow
gap in dedicated weak textures, while sampled photo/native targets contain
fine-frequency energy. The optional fine profile passes reader and actual V112
CPU training checks but has no trained-quality result and does not change the
completed Tiny/Small recipes.
The [V116 trial](v116-quality.md) has completed full review after that comparison,
combining the fine profile and reviewed paired masks while reusing completed
V114 as its matched Tiny control. Native256 mask-path/source/loss and actual
CUDA checks, complete evaluation, independent metrics and native review pass;
its analytic gain does not establish better natural-detail quality.

The latest [high-loss source review](v124-final-source-review.md) inspects40 new
IDs, retaining38 and withholding two grainy/artwork-heavy photos from a separate
future90,776-photo/35-region bank. One mixed-contrast leaf context is admitted;
down/fibre/rock proposals remain ordinary photos without specialized weak
annotations. The ledger has1,963 inspected IDs; this is targeted review rather
than uniform corpus-quality coverage. Existing trained/queued cohorts stay fixed.
The [illustrated source review](corpus-source-review.md) explains why
processing defects/nonphotographic targets are removed while difficult foliage,
textiles and weak real detail remain. Originals and historical manifests stay
read-only; protected captures and the GFX scene/siblings remain outside training.

Earlier [V93–V95](v43-curated-original20k-review.md) showed cleaner-data and
weak-detail gains on the older ViT-S model. [V96/V97](v95-flat-palette-quality-review.md)
and [V98/V99](v95-adc-training-quality-review.md) expose palette/ADC tradeoffs.
The complete reports retain favorable and adverse results. They do not require
using V43 as today's baseline.

[Reviewed corpus](commons-post4557-reviewed.md) ·
[Archive status](commons-download.md) ·
[Augmentation and selected-domain loading](training-pipeline.md) ·
[Native targets](public-raw-expansion-v2.md) ·
[Source/series exclusions](commons-content-overlap.md).

## Reading the evidence

Current guides and README images reflect useful available implementations.
Versioned reports retain the experiments' numerical results and protocols;
original decisions and chronology remain in the timestamped [diary](../diary/index.md).
Source/scene intervals describe the sampled cases, not training-seed uncertainty.
Real AHD/separate ISO100 references are not exact GT.

[Full-frame RGB16 measurements](mature-cudnn-fullframe.md) remain specific to
their checkpoints. Quality has priority over further speed work.
[Documentation guide](index.md) · [Research](research.md) ·
[Remaining project goals](requirements.md).
