# Current Small-model source review

**The latest16-source review prepares a90,784-source future cohort and six new
material regions.** It withholds one framed painting reproduction and one
photographed thermographic display from the next visible-light photographic
cohort. Fourteen sources remain eligible; six receive inspected weak-detail
regions in an optional20-region bank. This is curation/readiness evidence,
with trained-quality effects unmeasured. Active V122/V123 still use90,786 sources
and fourteen regions; V120/V121 retain their original inputs.

[Latest decisions, pixel reconstruction and actual reader](results/thin-photographic-materials-v1.json) ·
[Sixteen decisions and source credits, CSV](results/thin-photographic-materials-decisions-v1.csv) ·
[Prepared20-region targets](weak-photographic-targets.md#prepared20-region-material-extension).

## Latest photographic-domain decisions

These nominees come from an existing historical ADC-only target-statistic query,
not the live V121 loss stream. All sixteen full-source thumbnails and32 native256
source/area8-target cells were actually viewed. Six local original512/target64
pairs establish specific weak material structure. Three previously reviewed
bamboo/rod/sculpture contexts were also inspected for regions; their mixed/high
contrast did not justify a weak-region addition.

The painting reproduction's target is dominated by painted figures and canvas
texture. The thermographic capture shows false-color human silhouettes and
screen/raster texture. Both are valid retained media; their exact source IDs
are omitted only from a future cohort focused on visible-light photographic
targets. Physical carved stone, wood, plaster and etched metal remain eligible.
An “artwork” title or visible text alone does not decide source suitability.

![Painting reproduction withheld from the future cohort](images/weak-photographic-targets-20261026-v1/withheld-painting.png)

Source: [GoldenArtists, A Workshop of Nuns](https://commons.wikimedia.org/wiki/File:A_Workshop_of_Nuns_-_Alessandro_Magnasco.jpg),
[CC BY4.0](https://creativecommons.org/licenses/by/4.0/).

![Photographed thermographic display withheld from the future cohort](images/weak-photographic-targets-20261026-v1/withheld-thermographic-display.png)

Source: [böhringer friedrich, Thermografie Menschen](https://commons.wikimedia.org/wiki/File:Thermografie_Menschen_2.JPG),
[CC BY-SA2.5](https://creativecommons.org/licenses/by-sa/2.5/).
Modified by cropping, thumbnail creation, binning and ICC/display conversion;
only thumbnails resize. Source/cache files remain intact and read-only to this work.

The future4×/8× manifests remove exactly
`8cb7c7b865631ebfc88ac87df7bf1f0fe5509b48` and
`8e59071f5b1e4fcdb61f69b35c0f4f18f5aab16c`. Every other literal row and all
2,303/2,255 validation/test rows remain identical and ordered. The
[20-region catalogue](../configs/low-contrast-training-rois-cleaned90784-v1.json)
preserves all fourteen previous example objects. Its actual reader checks all20
constructor bindings and six new augmented regions, plus six unchanged controls.
No active source membership, recipe, sampling quota or training budget changes.

## Completed V120 loss-ranked inspection

The earlier28-source pass retained all28 photographs after five source sheets
and four larger native views. It changed no source membership. Its evidence is
preserved below, with the original selection and receipt scopes:

[Loss-ranked decisions and evidence](results/v120-source-loss-through18000-review-v1.json) ·
[All 28 decisions, source links and reasons, CSV](results/v120-source-loss-through18000-decisions-v1.csv) ·
[Independent selection and pixel checks](results/v120-source-loss-through18000-verification-v1.json) ·
[Publication bindings and live scheduling](results/v120-source-loss-through18000-publication-v1.json) ·
[Source/ROI/display metadata](images/v120-source-loss-through18000-v1/manifest.json).

### Nomination and actual inspection

The frozen V120 prefix through update 18,000 contains 1,616 Commons diagnostic
draws. This pass nominates only updates 5,001–18,000: 1,136 draws, including 795
photographic-branch draws from 761 IDs. The branch name alone does not establish
photographic content. Skipping 45 draws from fourteen already reviewed IDs
leaves 750 draws and 747 distinct eligible sources.

| Noise group | Eligible draws | Distinct IDs within group | Selected |
| --- | ---: | ---: | ---: |
| ADC-only: shot/read both zero | 76 | 76 | 6 |
| Positive sigma18 ≤ .005 | 281 | 281 | 6 |
| .005 < sigma18 ≤ .02 | 322 | 320 | 6 |
| sigma18 > .02 | 71 | 71 | 6 |
| Remaining highest gradient error | Same eligible pool | De-duplicated | 4 |

Here sigma18 = `sqrt(.18 × shot + read)` uses training coefficients, not measured
source-camera noise. An ID can appear in more than one group. Nomination takes
six distinct highest-loss IDs per group in the displayed order, then four
remaining distinct gradient-error cases. All 28 are new to the prior review
ledger. Evolving V120 weights, exposure and camera transforms confound losses;
these are inspection cues rather than fixed-endpoint or global quality scores.
[Trace definitions and limits](source-loss-diagnostics.md).

All five sheets were actually viewed: 28 source thumbnails and 56 unchanged
native256 source/target cells. Four ambiguous cases received native1024 views.
Strips below show full-source thumbnail → native source256 → area8 target256.
Only the thumbnail is resized. ICC-to-sRGB and exposure ×1 are recorded. Source
and target columns cover different fields of view: the source cell is centered
inside the larger binned-target context. Geometry/exposure/noise augmentation
from the nominated training update is not replayed.

### Retain difficult photographic detail

The bamboo bridge has continuous rails, thin irregular rods and rough joints.
Its native source has some grain/edge roughness, while the area8 target retains
coherent physical geometry. High loss is not a reason to discard these lines.

![Retained bamboo bridge: source context, native source and binned target](images/v120-source-loss-through18000-v1/thin-bamboo-bridge.png)

Source: [PIERRE ANDRE LECLERCQ, Pha Suam bridge](https://commons.wikimedia.org/wiki/File:Laos_Province_de_Champassak.-_cascade_de_Pha_Suam.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Modified by
cropping, thumbnail creation, binning and display conversion.

Weak grey folds and irregular pitting belong to a photographed sculpture.
The larger view supports retaining real material structure, without proving
that every small fluctuation is noiseless scene detail.

![Retained weak sculpted folds: source context, native source and binned target](images/v120-source-loss-through18000-v1/weak-sculpture-folds.png)

Source: [Spurzem, Madonna sculpture](https://commons.wikimedia.org/wiki/File:Bad_W%C3%B6rishofen,_Pfarrkirche_St._Justina_-_Madonna_mit_Kind_%282015-09-04_3470_Sp%29.JPG),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Same modifications.
[Actually viewed native1024 detail](images/v120-source-loss-through18000-v1/native1024-sculpture-folds.png).

A photograph of a physical rod sculpture is also retained. Rust, joints,
shadows and real thin geometry distinguish it from a standalone digital graphic.
A photographed information panel on a textured wall is retained for the same
reason. Titles containing “artwork” or visible text do not automatically exclude
photographs of real objects.

![Retained physical rod sculpture](images/v120-source-loss-through18000-v1/physical-rod-sculpture.png)

Source: [CEphoto, Uwe Aranas, PUSTEBLUME sculpture](https://commons.wikimedia.org/wiki/File:Forsbach_Germany_PUSTEBLUME-Artwork-Robin-Kurka-02.jpg),
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Same modifications.

The larger flower and plant views show focused petal/filament or foreground-tip
structure beside softer backgrounds. Source grain and saturated highlights
remain; this is not a claim of an unprocessed or noiseless capture. The area8
targets remain coherent under the current strategy.
[Native1024 plant focus](images/v120-source-loss-through18000-v1/native1024-plant-focus.png):
[Ireen Trummer, Kattekold](https://commons.wikimedia.org/wiki/File:Kattekold.JPG),
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/), cropped and color-managed without resizing.

## Current cohort and accumulated review

| Review scope | Distinct inspected sources | Retain | Withhold |
| --- | ---: | ---: | ---: |
| First 800 updates | 28 | 28 | 0 |
| Updates 801–5,000 | 28 | 27 | 1 |
| Updates 5,001–18,000 | 28 | 28 | 0 |
| New material/domain nomination | 16 | 14 | 2 |
| Total across these distinct recent scopes | 100 | 97 | 3 |

The earlier standalone roofing advertisement remains withheld from the 90,786
cohort: `e264392bcea19447f69f7d4599945de78f7e0c7c`.
[Its visual decision and coupled-manifest checks](results/v120-source-loss-through5000-review-v1.json)
are preserved, along with the [first800 decisions](results/v120-current-source-loss-review-v1.json).
V120/V121 retain their original 90,791/90,787-source bindings. V122/V123 use the
90,786-source cohort and [unchanged fourteen-region catalogue](../configs/low-contrast-training-rois-cleaned90786-v1.json).
That loss-ranked pass changed no source, manifest or catalogue. The new
material/domain pass prepares the90784/20-region alternative above while
preserving all active training inputs.

For the V120 through18,000 pass, independent checks verify all28 original JPEG
SHA1 and whole-cache SHA256
bindings, 5,505,024 exact native-source channel values and 5,505,024 area8 target
preview values. Twelve target channels differ by one DN8 at FP32/FP64 rounding;
all others match. Four native1024 views overlap the previous native256 crops at
786,432 exact channels. Sheet/individual-strip pixels and five published PNGs
match their actually viewed originals.

The de-duplication ledger now contains **1,659 IDs** across explicit prior
scopes. It is not a membership/exclusion list or a uniform corpus audit.
Whole-corpus cleanliness and trained-quality effects remain unproven. No neural
call, new noise, RAW decode, optimizer update or sampling-policy change is added
by this review.
