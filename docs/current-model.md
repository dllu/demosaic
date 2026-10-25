# Current model choices

**V114 Tiny is the general restoration and quality-training baseline.**
Its full-photo mean is36.97973dB, +.07735 over V112, with422/427 photo-source
means improving. Complete primary/analytic panels, independent saved-output
metrics, native review and102MP RGB16 exports are verified.
[Full Tiny/Small comparison](v114-v115-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General RAW and further quality work | **V114 Tiny**: photo36.97973dB; known/unseen CFA54.28627/54.00290dB; ADC mean/max bias7.08/51.73DN16 |
| Higher single-view photo score | **[V117 Tiny](v117-v118-quality.md)**: photo37.04408dB, +.06435 over V114; camera54.27303/53.97339dB and ADC max63.89DN16; remaining fine-detail softness |
| Higher measured known-camera mean / eight-pixel weak response | **V115 fitted Small**: photo36.97700dB; camera54.32405/54.00417dB; ADC max65.64DN16 and high-noise max106.79 versus Tiny85.40 |
| Optional eight-view V114 inference | [Fixed24 pilot](v114-eight-view.md): all12 material cases and both selected adverse camera crops improve; selected color bias rises slightly while spatial variation falls. Real fine detail remains soft; full panels/frame unmeasured; eight evaluations per tile |
| Exact parent and previously measured optional modes | [V112](v112-quality.md): photo36.90238dB, ADC maximum50.89DN16; [eight-view fixed24 pilot](v112-eight-view.md) improves all12 material cases, but full panels/frame remain unmeasured |
| Earlier full-panel eight-view option | [V104 dihedral8](dihedral-quality.md): photo37.04376dB, camera54.33283/53.99412dB; worse ADC maximum420.90DN16 and unresolved fine detail; eight evaluations per tile |
| Explicit ADC observed-sample fidelity | [V114 sites export](adc-consistency.md): ADC photo 37.78013→38.01575dB across 427 sources; worst color bias 51.73→37.82 DN16, with higher flat-field spatial RMS; positive-noise profiles bypass it |

Small has4/4 known-camera scene means above Tiny and a slightly higher unseen
mean, with3/5 scenes rising. Tiny has slightly higher photo PSNR and lower color
bias. Both improve over V112. This selects a useful general balance without
hiding Small's gains or applying an old study-specific promotion threshold.

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
`/mnt/external/demosaic/models/v114-final20000.pt`, SHA256
`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2`.
The architecture retains V84's pretrained DRUNet RGB trunk, physical
noise/camera conditioning and official frozen DINOv3 ConvNeXt-Tiny pyramid.
[Inference and linear DNG/JPEG usage](usage.md).

The useful V117 photo-score option is
`/mnt/external/demosaic/models/v117-final20000.pt`, SHA256
`f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0`.
Its modest photo and weak-carrier gains coexist with lower camera means and
higher ADC bias. Choosing V114 for camera/color balance does not hide V117's
progress or impose a study-specific promotion gate.

The [Q2/Sony/GFX50R gallery](cross-camera-qualitative.md) now compares both
current models with V104 and both released RawNIND variants on the same cached
inputs. Version differences are small in these six low-ISO regions; dark rocks
and window edges stay soft. Concrete texture looks finer than RawNIND, with no
clean reference establishing every fluctuation as real detail.

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
Full quality review is running; the additional fine-mesh comparison shows no
clear lattice-recovery gain over V115 at matched noise conditioning.

## Quality and remaining work

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

[PSNR history](performance-history.md) includes both new endpoints.
The [fixed V115/V117 output mean](fixed-tiny-small-mean.md) gives an intermediate
tradeoff: photo 37.02408dB and camera 54.31387/54.00195dB. It loses photo score
to V117 and camera means to V115, with unchanged visible GFX fine-detail loss.
This completed saved-output study does not establish a better trained architecture.
[Native review and publication checks](results/fixed-tiny-small-mean-review-v1.json).
Earlier useful comparisons retain their exact checkpoints and receipts:
[V112](v112-quality.md), [V104](v104-reviewed-corpus-quality.md),
[V102/V103](v102-v103-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
