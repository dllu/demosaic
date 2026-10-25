# Current model choices

**V114 Tiny is the general restoration and quality-training baseline.**
Its full-photo mean is36.97973dB, +.07735 over V112, with422/427 photo-source
means improving. Complete primary/analytic panels, independent saved-output
metrics, native review and102MP RGB16 exports are verified.
[Full Tiny/Small comparison](v114-v115-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General RAW and further quality work | **V114 Tiny**: photo36.97973dB; known/unseen CFA54.28627/54.00290dB; ADC mean/max bias7.08/51.73DN16 |
| Higher measured known-camera mean / eight-pixel weak response | **V115 fitted Small**: photo36.97700dB; camera54.32405/54.00417dB; ADC max65.64DN16 and high-noise max106.79 versus Tiny85.40 |
| Exact parent and previously measured optional modes | [V112](v112-quality.md): photo36.90238dB, ADC maximum50.89DN16; [eight-view fixed24 pilot](v112-eight-view.md) improves all12 material cases, but full panels/frame remain unmeasured |
| Earlier full-panel eight-view option | [V104 dihedral8](dihedral-quality.md): photo37.04376dB, camera54.33283/53.99412dB; worse ADC maximum420.90DN16 and unresolved fine detail; eight evaluations per tile |
| Explicit ADC observed-sample fidelity | [V104 sites export](adc-consistency.md): +.28850dB on full ADC photo panel over original V104; color/detail tradeoffs remain |

Small has4/4 known-camera scene means above Tiny and a slightly higher unseen
mean, with3/5 scenes rising. Tiny has slightly higher photo PSNR and lower color
bias. Both improve over V112. This selects a useful general balance without
hiding Small's gains or applying an old study-specific promotion threshold.

## Run the current model

[Explicit selection](../configs/current-model.json):
`/mnt/external/demosaic/models/v114-final20000.pt`, SHA256
`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2`.
The architecture retains V84's pretrained DRUNet RGB trunk, physical
noise/camera conditioning and official frozen DINOv3 ConvNeXt-Tiny pyramid.
[Inference and linear DNG/JPEG usage](usage.md).

V114 adds20k updates to the V112 EMA at seed63, using90,864 reviewed Commons
sources, native128/paired32 targets,4×→geometry→area2, zero optical PSFs,
weak textures and photographic contrast attenuation. Reconstruction epsilon
is.0003; paired RAW retains.0001. [Matched training](small-aligned-training.md).
V115 changes the official frozen encoder and eight fitted lateral initializers,
keeping the remaining V112 trunk/gate tensors and the matched training budget.
It is a fitted-transfer comparison, not capacity alone.

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

The [V116 data trial](fine-detail-data-training.md) has passed its CUDA check
and started its original20k run. It holds Tiny's architecture fixed against
completed V114 while testing fine weak sources and reviewed reference masks.
Its original V112 initializer, control, seed and schedule remain unchanged.
Trained quality and native review are pending. Quality precedes speed.

[PSNR history](performance-history.md) includes both completed endpoints.
Earlier useful comparisons retain their exact checkpoints and receipts:
[V112](v112-quality.md), [V104](v104-reviewed-corpus-quality.md),
[V102/V103](v102-v103-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
