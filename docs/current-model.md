# Current model choices

**V120 Small is the current general restoration and quality-development recommendation.**
Its primary panels, native synthetic triplets, full local statistics and selected
native review are complete. Photo37.04008dB and known/unseen54.31272/54.00872dB
coexist with a much lower tested ADC maximum than V119:55.52DN16.
[Matched-profile full-frame comparisons](v120-v121-primary.md#matched-profile-full-frame-gfx)
against V115/V119 are complete; differences remain subtle and fine detail stays soft.
[V120/V121 measured gains and remaining limits](v120-v121-primary.md).
Quality development uses the Small architecture; active V122/V123 keep their
fixed V115 parent for the controlled frequency-scope comparison.
V114's full-photo mean is36.97973dB, +.07735 over V112, with422/427 photo-source
means improving. Complete primary/analytic panels, independent saved-output
metrics, native review and102MP RGB16 exports are verified.
[Full Tiny/Small comparison](v114-v115-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General RAW and quality development | **[V120 Small](v120-v121-primary.md)**: photo37.04008dB; known/unseen54.31272/54.00872dB; ADC maximum55.52DN16; recovers V119 camera/color regressions. Remaining mesh softness and GFX profile-comparison limits are explicit |
| Fully reviewed Tiny alternative / lower tested ADC maximum | **V114 Tiny**: photo36.97973dB; known/unseen CFA54.28627/54.00290dB; ADC mean/max bias7.08/51.73DN16 |
| Higher single-view photo score | **[V117 Tiny](v117-v118-quality.md)**: photo37.04408dB, +.06435 over V114; camera54.27303/53.97339dB and ADC max63.89DN16; remaining fine-detail softness |
| Higher measured known-camera mean / eight-pixel weak response | **V115 fitted Small**: photo36.97700dB; camera54.32405/54.00417dB; ADC max65.64DN16 and high-noise max106.79 versus Tiny85.40 |
| Optional eight-view V114 inference | [Fixed24 pilot](v114-eight-view.md): all12 material cases and both selected adverse camera crops improve; selected color bias rises slightly while spatial variation falls. Real fine detail remains soft; full panels/frame unmeasured; eight evaluations per tile |
| Exact parent and previously measured optional modes | [V112](v112-quality.md): photo36.90238dB, ADC maximum50.89DN16; [eight-view fixed24 pilot](v112-eight-view.md) improves all12 material cases, but full panels/frame remain unmeasured |
| Earlier full-panel eight-view option | [V104 dihedral8](dihedral-quality.md): photo37.04376dB, camera54.33283/53.99412dB; worse ADC maximum420.90DN16 and unresolved fine detail; eight evaluations per tile |
| Explicit ADC observed-sample fidelity | [V114 sites export](adc-consistency.md): ADC photo 37.78013→38.01575dB across 427 sources; worst color bias 51.73→37.82 DN16, with higher flat-field spatial RMS; positive-noise profiles bypass it |

In the earlier controlled comparison, V115 Small has4/4 known-camera scene means
above V114 Tiny and a slightly higher unseen mean, with3/5 scenes rising. V114
has slightly higher photo PSNR and lower color bias in that pair. Both improve
over V112. The newer V120 continuation supplies the measured general balance
above without applying a study-specific promotion threshold.

The [V114 eight-view pilot](v114-eight-view.md) is complete on the same24 saved
inputs as V112. Material gains average+.55750/.26416/.07938dB at ADC/ISO100/
ISO12800; both selected camera crops improve, with a small selected color-bias
tradeoff. Independent mean/metric checks and native review pass. This qualifies
a useful optional mode without claiming full427/all-camera/full-color-grid or
complete102MP results. The original V116 training/review chain is unchanged.

The [local material diagnosis](local-material-detail.md) finds substantial
remaining weak-detail attenuation: high-noise eight-view gain is.31813 in the
lowest contrast group, drawn only from feather/fur. Averaging slightly lowers
gain and residual error together. This complements the whole-patch scores and
does not change the general photo/color baseline choice.

## Run the current model

[Explicit selection](../configs/current-model.json):
`/mnt/external/demosaic/models/v120-final20000.pt`, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
The architecture retains V84's pretrained DRUNet RGB trunk, physical
noise/camera conditioning and official frozen DINOv3 ConvNeXt-Small pyramid.
[Inference and linear DNG/JPEG usage](usage.md).

The useful V117 photo-score option is
`/mnt/external/demosaic/models/v117-final20000.pt`, SHA256
`f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0`.
Its modest photo and weak-carrier gains coexist with lower camera means and
higher ADC bias. The current V120 recommendation keeps V117 available for its
higher photo mean and V114 for its lower tested ADC maximum.

The V114 Tiny alternative remains available at
`/mnt/external/demosaic/models/v114-final20000.pt`, SHA256
`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2`.
[Verified immutable endpoint aliases](results/v120-v121-endpoint-aliases-v1.json)
also preserve V121 for reproducible comparison. The
[selection change](results/current-model-v120-selection-v1.json) preserves the
previous selector and plot bytes. All five active plans pass their binding guards
before and after the change; their fixed V115 parents and inputs stay unchanged.

The [Q2/Sony/GFX50R gallery](cross-camera-qualitative.md) now compares both
current models with V104 and both released RawNIND variants on the same cached
inputs. Version differences are small in these six low-ISO regions; dark rocks
and window edges stay soft. Concrete texture looks finer than RawNIND, with no
clean reference establishing every fluctuation as real detail.

The [completed camera-linear development comparison](native-camera-development.md#v120v121-extension)
also includes V120/V121 on11 binned captures under added noise. V120 exceeds
RawNIND by3.69903dB in high-noise camera-RGB PSNR and retains substantially finer
native texture. V117 still has higher condition means; V121 changes only slightly.
Low-noise reference estimates and added-noise inputs do not establish broad
real high-ISO superiority.

V114 adds20k updates to the V112 EMA at seed63, using90,864 reviewed Commons
sources, native128/paired32 targets,4×→geometry→area2, zero optical PSFs,
weak textures and photographic contrast attenuation. Reconstruction epsilon
is.0003; paired RAW retains.0001. [Matched training](small-aligned-training.md).
V115 changes the official frozen encoder and eight fitted lateral initializers,
keeping the remaining V112 trunk/gate tensors and the matched training budget.
It is a fitted-transfer comparison, not capacity alone.

The [full saved-output local-detail comparison](local-material-detail.md#tiny-versus-fitted-small-on-the-same-full-photo-support)
now covers the same427 sources for both encoders. Weak natural-detail response
is nearly unchanged; Small's camera and eight-pixel advantages make it a useful
parent for the [V119 cleaned-data trial](cleaned-diverse-small-training.md), without suggesting that size alone fixes
faint detail. The [reviewed83-ID paired extension](paired-camera-sampling.md)
retains corrected reference masks and the original camera proportions. Both
discarded implementation checks passed and all20k training updates completed.
[V119's full review is complete](v119-quality.md): photo37.03831dB, a+.06131dB
gain over V115, but known/unseen54.10063/54.00742dB and ADC maximum2526.70DN16.
Weak high-noise photographic gain changes only.36422→.36523; no clear real
fine-mesh gain appears at matched conditioning. These camera/color regressions
favor retaining the useful choices above. The
[native-camera development comparison](native-camera-development.md) finds
much finer detail than RawNIND on its11 binned captures under added noise,
with V117 still slightly ahead of V119. This does not establish broad real
high-ISO superiority.

The [V120/V121 follow-up](paired32-weak-detail-training.md) keeps the V115 Small
architecture, tests corrected paired32 against V119's expansion, then tests the
reviewed90787-source/fourteen-region intervention at a matched20k budget.
Both original20k runs and independent numerical audits are complete. V120 keeps
V119's photo score with a+.21209dB known-camera recovery and much lower tested
ADC maximum. V121's small photo/known changes coexist with lower unseen mean
and a large ADC tail. [Two native exact-GT triplets per model](v120-v121-primary.md)
are published; full local statistics and selected native review are complete. Older Haar/new nominal
GFX conditioning is labeled; the additional fixed-Haar full-frame operators
now match older V115/V119 inputs exactly, with no clear large detail recovery.

## Quality and remaining work

The [completed V128 early-feature pilot](v128-feature-pilot-quality.md) finds no
useful gain against V126 after1,000 matched updates. Independent scoring and
all28 native boards, including both GFX pairs, are complete. The feature term
stays off by default. The [completed V129 curated27-region pilot](reviewed-detail-training-pilot.md)
also shows no useful visible recovery at1k, with+.00093dB ordinary/+.00042dB shadow
sRGB changes versus V126. All28 native boards are reviewed. The
[audited precision-gradient diagnostic](training-precision-gradients.md) led to
the [completed V130 matched FP32 trial](training-precision-pilot.md) against saved
V129 BF16. Ordinary/shadow sRGB changes are+0.00009/+0.00055dB; all28 native
boards show no clear large noisy-detail or real-mesh recovery. V120 remains the
general recommendation.

An optional [RAW spatial-attention branch](raw-spatial-features.md) now passes
genuine-V120 CPU/CUDA16+2 implementation checks. It adds22,664 parameters with
zero initial effect and a constant-preserving feature path. Model quality remains
unmeasured; the original V124/V125 mean-loss trial and current V120 choice stay fixed.

The completed48-call [faint ADC comparison](faint-adc-precision.md) shows V130's
slightly stronger gain and lower relative error in selected weak fur, grass and
wood strata against V129. Global faint-target sRGB PSNR falls0.01720dB and native
changes are subtle. Normal and fixed40× display comparisons are published.
The completed [V122/V123 frequency trial](v122-v123-quality.md) raises V123's
photo mean by0.05493dB against adapter-only V122, with lower unseen-camera mean
and ADC maximum4190.02DN16. Weak natural-detail gain changes only0.36465→0.36500;
both real GFX scenes remain soft. Full numerical/selected native review is complete.

The [independent-noise diagnostic](conditional-noise-response.md) separates
persistent error from output variance on four fixed targets. Faint fur/wood
remain biased after averaging independent V120/V117 restorations; strong bark
is mainly variance-limited. This supports testing a conditional-mean loss,
without an inference-strength or recommendation change. The multi-observation
mean is a diagnostic unavailable from one capture.
[V124/V125 now implement the matched training trial](conditional-mean-training.md)
on the cleaned90784/twenty-region data. V124's two-noise-view control is now
training; quality is unmeasured.

At2% contrast/ISO12800, Tiny's eight/sixteen-pixel carrier gains rise to
.13371/.71335; Small reaches.15217/.68865. Four-pixel structure remains nearly
absent. Native material/GFX examples show soft fine foliage and saturated signs,
and dark-camera mottling persists. The stronger released RawNIND reference
still wins four of nine camera scene means. Broad real-camera superiority
and state-of-the-art quality remain unproven. Separate ISO100/AHD RGB references
are not exact GT.

Both complete101.996MP outputs are verified. Ordered FP32 inference/blending
observations are116.57s for Tiny and101.66s for Small; differing warmup/workspace
states prevent a speed ranking. The100MP/10s target remains open. Hot-pixel
repair and [linear DNG/JPEG export](dng-export.md) are available; repair was off
in these comparisons. [Camera-outlier diagnostics](camera-outliers.md).

The [completed V116 data trial](v116-quality.md) holds Tiny's architecture fixed
while testing fine weak sources and reviewed reference masks. Eight-pixel weak
carrier gain rises from.13371 to.19123, but full-photo/unseen-CFA means fall
slightly, broad weak-material gain is unchanged and ADC worst bias rises to
239.15DN16. Native GFX foliage/neon softness remains. V114 retains the better
general balance; the new gains and weaknesses remain documented. Quality precedes speed.

The [completed V117/V118 loss pair](v117-v118-quality.md) starts directly from
V114 with matched20k budgets and common corrected data. V117's photo mean rises
to37.04408dB, with421/427 sources improving. V118's band term lowers weak natural
response against its control and worsens the ADC maximum to843.05DN16 despite a
small eight-pixel carrier gain. Complete metrics, native material/GFX comparisons
and RGB16 checks are published. Keep the term off for further quality work;
architecture and parent remain choices guided by their measured tradeoffs.

[PSNR history](performance-history.md) includes V120/V121 and earlier reviewed endpoints.
The [fixed V115/V117 output mean](fixed-tiny-small-mean.md) gives an intermediate
tradeoff: photo 37.02408dB and camera 54.31387/54.00195dB. It loses photo score
to V117 and camera means to V115, with unchanged visible GFX fine-detail loss.
This completed saved-output study does not establish a better trained architecture.
[Native review and publication checks](results/fixed-tiny-small-mean-review-v1.json).
Earlier useful comparisons retain their exact checkpoints and receipts:
[V112](v112-quality.md), [V104](v104-reviewed-corpus-quality.md),
[V102/V103](v102-v103-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
