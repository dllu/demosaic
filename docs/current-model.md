# Current model choices

**V112 final20k is the working restoration and quality-training baseline.**
It reaches36.90238dB on all427 photos, +.10154dB over V104, with425 source means
improving. It keeps V111-like photo quality while raising both camera means and
reducing worst ADC flat bias to50.89DN16. [Complete review and native images](v112-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General photographic RAW and further quality training | **V112**: photo36.90238dB; known/unseen CFA54.26914/53.95378dB; ADC mean/worst bias7.45/50.89DN16 |
| Near-equal photographic alternative | V111: photo36.90367dB, but lower camera means and ADC maximum2,142.98DN16 |
| Explicit ADC sample fidelity/photo PSNR | Optional [V104 sites export](adc-consistency.md): +.28850dB over original V104 on full ADC photo panel; color/detail tradeoffs remain |
| Separate earlier camera reference | V102: unseen CFA53.97177dB remains slightly higher; its overall photo mean is36.67951dB |
| Optional eight-view inference | Tested [V104 pilot](dihedral-quality.md); eight evaluations per tile. Broad panels/export/audit continue separately from V112 selection |

## Run the current model

The explicit selection is [configs/current-model.json](../configs/current-model.json).
Checkpoint: `/mnt/external/demosaic/models/v112-final20000.pt`, SHA256
`21c3cca8370df21e3412f9ccbf441c35afcfad8fd03174c7727f4f88874783b1`.
The architecture is V84's pretrained DRUNet RGB trunk with physical noise/camera
conditioning and the official frozen DINOv3 ConvNeXt-Tiny pyramid. The matched
V111/V112 trial retains all learned fusion gates. [Inference and DNG/JPEG usage](usage.md).

The fixed20k continuation uses90,864 reviewed Commons sources, native128/paired32
RAW targets,4×→geometry→area2, zero optical PSFs, weak textures and photographic
contrast attenuation. Epsilon.0003 is the trained change against V111's.001;
paired RAW keeps.0001. [Recipe and execution](loss-scale-training.md).

## Quality and limits

V112 improves every full-photo condition mean over V104. Relative to V111,
photo change is−.00129dB while camera means rise+.01644/+.01672dB and the large
ADC color tail disappears on the complete grid. All4704 retained color
predictions pass an independent Torch64 arithmetic check. Native synthetic
triplets, analytic failures and all six standing GFX regions are in the
[performance report](v112-quality.md).

At2% contrast/ISO12800,8/16-pixel carrier gains rise to.09580/.65759, but4-pixel
structure is nearly absent. Real foliage and saturated-light detail remain
soft. The [stronger released RawNIND reference](rawnind-variants.md) remains
competitive on camera scenes; broad real-camera superiority is not achieved.
The separate ISO100 GFX exposure and AHD references are not exact RGB GT.

All seven matched panels and complete101.996MP V112 RGB16 exports are
verified. V112 FP32 inference/blending takes167.51s; V104's earlier168.73s
observation remains a separate checkpoint measurement. The100MP/10s target stays open, with quality first.
Hot-pixel repair and [linear DNG/JPEG export](dng-export.md) are available;
repair was off in these comparisons.

## Next architecture work and references

The [Small feature-transfer method](small-feature-transfer.md) preserves learned
gates through a training-only fit. Its V104-derived initializer passed eight
actual CPU optimizer updates, but the idle V113 queue was superseded before
any GPU training after V112's stronger results. [Current rebase and preserved
evidence](small-aligned-training.md). Reuse cached Small features/previews for
a V112-teacher fit, then fresh checks and an explicit training budget.

Earlier results remain useful and their receipts unchanged:
[V104](v104-reviewed-corpus-quality.md), [V102/V103](v102-v103-quality-review.md),
[V100/V101](v84-curated-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
[PSNR history](performance-history.md) plots completed primary endpoints with
unequal budgets/data; study-specific promotion gates do not freeze this choice.
