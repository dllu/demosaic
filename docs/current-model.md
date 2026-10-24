# Current model choices

**V112 final20k is the working restoration and quality-training baseline.**
It reaches36.90238dB on all 427 photos, +.10154dB over V104, with425 source means
improving. It keeps V111-like photo quality while raising both camera means and
reducing worst ADC flat bias to50.89DN16. [Complete review and native images](v112-quality.md).

| Use | Current choice and tradeoff |
| --- | --- |
| General photographic RAW and further quality training | **V112**: photo36.90238dB; known/unseen CFA54.26914/53.95378dB; ADC mean/worst bias7.45/50.89DN16 |
| Near-equal photographic alternative | V111: photo36.90367dB, but lower camera means and ADC maximum2,142.98DN16 |
| Explicit ADC sample fidelity/photo PSNR | Optional [V104 sites export](adc-consistency.md): +.28850dB over original V104 on full ADC photo panel; color/detail tradeoffs remain |
| Separate earlier camera reference | V102: unseen CFA53.97177dB remains slightly higher; its overall photo mean is36.67951dB |
| Optional eight-view inference with current V112 weights | [Fixed24 comparison](v112-eight-view.md): all12 material PSNRs improve, mean gains+.543/.273/.079dB at ADC/ISO100/ISO12800; two adverse camera crops and four color cases improve over single view. Real fine detail remains soft; full panels/frame unmeasured; eight evaluations per tile |
| Eight-view full-panel reference | [Completed V104 full panels](dihedral-quality.md): photo37.04376dB, known/unseen54.33283/53.99412dB; all427 photo-source means improve over V104 single. ADC max420.90DN16 remains worse than V112 single |

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

All seven matched panels and complete 101.996MP V112 RGB16 exports are
verified. V112 FP32 inference/blending takes167.51s; V104's earlier168.73s
observation remains a separate checkpoint measurement. The100MP/10s target stays open, with quality first.
Hot-pixel repair and [linear DNG/JPEG export](dng-export.md) are available;
repair was off in these comparisons.
The [supplementary camera-outlier study](camera-outliers.md) tests existing
isolated repair with both V112 and stronger RawNIND. It localizes a large museum
deficit to one bright sample and finds recurring reference-supported sensor
points; it does not establish a broad repaired-input winner or change defaults.

## Next architecture work and references

The [Small feature-transfer method](small-feature-transfer.md) now preserves
V112's learned gates and trunk through a training-only lateral fit. Photo means
stay close; two adverse-camera crops remain .20–.32dB worse. Matched V114 Tiny
and V115 fitted Small passed eight actual CPU and CUDA updates each;
[V114 has completed 20,000 updates and V115 is training](small-aligned-training.md).
Each receives 20,000 further updates at seed 63. Endpoint quality remains pending.

The [V116 data trial](fine-detail-data-training.md) is queued after that exact
review chain. It holds Tiny's architecture fixed to reuse completed V114 as the
equal-budget control, testing fine weak sources and reviewed reference masks.
Its trained quality is unmeasured; the larger-encoder recommendation can still
advance when the Small results are reviewed.

Earlier results remain useful and their receipts unchanged:
[V104](v104-reviewed-corpus-quality.md), [V102/V103](v102-v103-quality-review.md),
[V100/V101](v84-curated-quality-review.md), [V84/V85](native-data-original20k-review.md)
and [V43-family cleaned-data trials](v43-curated-original20k-review.md).
[PSNR history](performance-history.md) plots completed primary endpoints with
unequal budgets/data; study-specific promotion gates do not freeze this choice.
