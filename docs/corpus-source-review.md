# Training-source quality review

Source quality decisions support the current [V84-based quality experiments](quality-first-training.md).
**530 training sources have now been visually reviewed: 500 retained and 30
withheld.** The active V100/V101 runs keep their original 88,484-source cohort,
which applies the earlier 24 exclusions. Six additional exclusions are prepared
in a separate cohort for later training; they do not change the active study.

| Cohort | Commons training sources | Validation / test | Visual exclusions |
| --- | ---: | ---: | ---: |
| Active V100/V101 | 88,484 | 2,303 / 2,255 | 24 |
| Prepared follow-up | 88,478 | Same exact records | 30 |

[Latest decisions, figures and cohort checks](results/source-quality-followup110-review-v1.json).
Originals, existing manifests and protected evaluation scenes remain read-only.
The GFX train/platform pair and siblings remain outside training.

## Selection and inspection

The prepared pool contains 88,508 eligible Commons training sources at 4×/8×
binning. The completed V43 scan scores all of them under ADC-only and ISO 12800
priors: 177,016 cases and 22,128 neural/DINO forwards. It uses IEEE FP32, a
native center crop and final area2 reduction, without geometric or optical
augmentation. Its [completion and original cohort freeze](results/v43-quality-curation-and-training-plan-v1.json)
retain source, loss, membership and owner checks. The older model's loss is a
review cue, rather than a current quality ranking or an exclusion rule.

All **319 unique candidates** in the saved top 128 per-condition loss lists,
lowest-gradient 64, highest-Laplacian 64 and brightest 32 lists now have actual
visual decisions. Other reviewed sources include title/metadata cues, all 74
training sources with recorded ISO ≥12800, and weak/fine material examples.
The latest pass inspected the remaining 110 candidates on 19 source sheets and
six larger native 1024×1024 crops, retaining 104 and withholding 6. This targeted
coverage does not estimate the defect rate of the full corpus.

Inspect source context, native pixels and the actual binned target for grain,
blur, flattened texture, exaggerated outlines and non-photographic compositions.
Keep genuine hard detail: foliage, textiles, fences, painted/glazed materials,
engraved lettering, weak fog and skies. Natural defocus or exposure-integrated
motion is not automatically a defect. Grain that largely disappears after
binning need not invalidate the target. White backgrounds, high ISO, HDR or
stacking tags alone do not decide exclusion.

The figures below show a resized full-source thumbnail, a native 256×256 source
crop and a native 256×256 8×-binned target. The native views have different physical
fields of view. Only the thumbnail is resized; exposure is ×1. These are
source-quality inspections, without simulated noise or model restoration.

## Latest exclusions

Five sources are flat front/back banknote composites dominated by printed text
and illustration: Rothenburg, Berchtesgaden, Neustadt, Bad Oeynhausen and Berlin.
Their assembled document presentation falls outside the photographic target.
Photographs of actual mounted signs, engraved metal, book pages, stained glass
and mosaics remain eligible when their material and scene detail are coherent.

![Withheld banknote composite: source context, native source and binned target](images/source-quality-banknote-composite.png)

Source: [Christoph Scheibenberger, Rothenburg 50 Pfennig 1918](https://commons.wikimedia.org/wiki/File:Rothenburg_50_Pfennig_1918.jpg),
public domain. Modified through binning, cropping and context-thumbnail creation.
[Source hashes, ROIs and display metadata](results/source-quality-banknote-composite.json).

The sixth source has flattened leaf surfaces and strongly edged, patchy
boundaries in the larger native view, with residual patchiness in the binned
target. Withholding it is a visual clean-target judgment; no particular
processing tool is inferred. Other fine foliage sources remain eligible.

![Withheld foliage: source context, native source and binned target](images/source-quality-paseo-foliage.png)

[1024×1024 source crop, without resizing](images/source-quality-paseo-foliage-native1024.png).
Source: [Lmbuga, Paseo con bancos na Alameda de Santiago](https://commons.wikimedia.org/wiki/File:2025_Paseo_con_bancos_na_Alameda_de_Santiago._Galiza.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified through
binning, cropping, display conversion and context-thumbnail creation.
[Source hashes, ROIs and decision](results/source-quality-paseo-foliage.json).

Earlier exclusions include a map, non-photographic compositions, a predominantly
defocused scene and unreliable texture/edge targets. The illustrated
[flattened-foliage example](images/source-quality-flattened-foliage.png)
([metadata](results/source-quality-flattened-foliage-example.json)) and
[altered-feather example](images/source-quality-processed-feathers.png)
([metadata and credits](results/source-quality-gallery-v1.json)) retain their
original evidence.

## Retain weak and fine detail

The latest pass retains 104 useful sources, including dense fish, leaves, mesh,
small circuitry, stained glass, weak cloud/sky boundaries and atmospheric scenes.
The larger forest view has visible native grain, but binning suppresses it
while retaining faint tree structure. Its low contrast is useful training data.

![Retained forest: source context, native source and binned target](images/source-quality-retained-weak-forest.png)

Source: [Ermell, Neubürg Winter Wald](https://commons.wikimedia.org/wiki/File:Neub%C3%BCrg_Winter_Wald_2183874.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified through
binning, cropping, display conversion and context-thumbnail creation.
[Source hashes, ROIs and decision](results/source-quality-retained-weak-forest.json).
Earlier [leaf-vein](images/source-quality-retained-leaf.png) and
[weak-fog](images/source-quality-retained-fog.png) examples also remain eligible;
the [gallery metadata](results/source-quality-gallery-v1.json) retains their
credits and native-view protocols.

## Cohort use

The active manifest is
`.cache/quality-first-20261020/curated-corpus-v1/manifest4-large.jsonl`.
The follow-up manifest is
`.cache/current-quality-20261022-v1/source-review-v1/future-cohort/manifest4-large.jsonl`,
SHA256 `e5dafbbf6b301641306c7c451dac229f8340b848e773ea74b0434c2895f1fb45`.
It removes only the six newly withheld training IDs. Every remaining row is an
unchanged byte-for-byte subset; validation/test records and order are identical.
All 530 reviewed decisions agree with its membership. Neither active recipe
uses this follow-up manifest yet.

For reviewed-region sampling on that manifest, use the
[companion catalogue](../configs/low-contrast-training-rois-curated-v2.json).
It binds the new manifest path/SHA while preserving all six source records,
coordinates and ROI/target hashes. The reader requires this exact binding;
the original catalogue remains attached to the active cohort. Actual CPU data
reads of all six regions pass with the follow-up manifest.

Source views read cached Commons originals from `/mnt/external/qi` and prepared
linear-sRGB caches. Current training and GFX tests avoid source HDD access.
New downloads and decisions enter a new frozen cohort instead of silently
changing an existing run's inputs.

## Reviewed weak and fine texture ROIs

The [six-region catalogue](../configs/low-contrast-training-rois-v1.json) records
existing training sources with hash-verified 512×512 contexts in the 4× cache;
final area2 gives native 256×256 targets. The
[opt-in reader](training-pipeline.md#reviewed-photographic-regions) validates
membership, hashes and bounds before sampling and augmentation.
**V101 enables conditional 5% photographic ROI sampling; V100 leaves it off.**
Their production quality comparison is pending. The catalogue and active
manifests remain unchanged by this follow-up source review.

| Source ID prefix | Inspected structure | Bin4 context [x,y,w,h] |
| --- | --- | --- |
| `6aa3e94bda50` | Gray wool fibers and wrapped thread | [160,0,512,512] |
| `423c08bacc74` | Faint fishing-net lines; face outside this ROI | [288,256,512,512] |
| `7b56d20ffd21` | Fine gray wire braid grooves | [96,360,512,512] |
| `a4ae82e1e5b6` | Subtle grain on white-painted fence boards | [504,280,512,512] |
| `ed29eebff641` | Pale lichen filaments against bark | [96,8,512,512] |
| `9b4e6f950b1d` | Same-color cloth folds and crease edges, without claiming resolved fibers | [384,128,512,512] |

These are regions containing weak/fine structures, rather than global
low-contrast labels. The [source/ROI review](results/low-contrast-training-source-review-v1.json)
and [CPU reader validation](results/reviewed-ROI-loader-CPU-readiness-v1.json)
record actual views, hash checks, augmentation order and resume behavior.
