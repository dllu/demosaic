# Weak photographic material targets

The **14-region catalogue** preserves the original six training regions
and adds eight existing photographs with inspected low-contrast material detail.
It is selected for **V121 on90,787 sources** and passes actual reader plus
discarded16-update CPU/CUDA checks. V121's full run is queued after V120;
its endpoint quality effect remains unmeasured. V119/V120 retain six regions,
90,791 sources and the same5% conditional-photo ROI probability.
[Matched training and queued review](paired32-weak-detail-training.md).

A [future90,786-source snapshot](current-source-loss-review.md) removes one
separately inspected nonphotographic advertisement while preserving all fourteen
region objects, source pixels and target hashes. Its
[rebound catalogue](../configs/low-contrast-training-rois-cleaned90786-v1.json)
passes actual source/crop/target and sampler checks. V121 keeps its original
90,787-source binding; the future snapshot launches no new training job.

[Catalogue](../configs/low-contrast-training-rois-cleaned90787-v1.json) ·
[Actual visual decisions](results/weak-photographic-targets-review-v1.json) ·
[Preparation and source reconstruction](results/weak-photographic-targets-preparation-v1.json) ·
[Completed actual-reader check](results/weak-photographic-targets-v1.json).

## Selection and limits

The earlier six-versus32 study had a tiny mixed quality effect, so adding more
regions at the same quota is not an established improvement. This bank prepares
a different set of measured weak targets for a later deliberate experiment.
No new source, sampling quota, loss mask, optical blur or noise policy is applied.

The first twelve material nominees contained useful fine detail, but six local
source/target pairs showed substantial mixed contrast and broad edges. Those
photographs remain eligible under ordinary sampling. A second query uses the
completed historical source screen to find 195 active candidates with mean-RGB
linear SD .015–.05, gradient RMS .0015–.025 and clipped fraction at most .01,
outside the earlier 32-region catalogue. These statistics nominate inspection;
they do not establish photographic quality. They are target statistics, not
current V119 per-source losses.

Sixteen varied physical subjects from that query were actually viewed. Eight
are selected; the other eight retain ordinary membership. Blank sky and smooth
backgrounds can satisfy a low global contrast statistic while offering little
fine detail. Reflective insect edges and dark artifact outlines are useful
photography, but do not automatically qualify as weak material texture.

| New source prefix | Inspected structure | Aligned bin4 context xywh | Local64 luminance SD |
| --- | --- | --- | ---: |
| `cb53d7496cb2` | Dark snowy roofs and thin branches | [744,494,512,512] | .01139 |
| `924e8a6601b5` | Worn plaster and pigment boundaries | [270,622,512,512] | .02557 |
| `1306f44f2652` | Bronze patina and shallow relief | [68,200,512,512] | .01768 |
| `824b0ae351e6` | Fine brick ceiling grid | [410,138,512,512] | .02221 |
| `ec4283295d51` | Faint plaster cracks and mottling | [222,86,512,512] | .02023 |
| `0c95cdbe2430` | Naturally soft wet-mud ridge boundaries | [278,100,512,512] | .01178 |
| `9e5e95d6c657` | Fine sea-surface wavelets | [358,160,512,512] | .02108 |
| `ad7a3b8a9e12` | Faint sand-ripple ridges | [320,176,512,512] | .02727 |

Local SD uses Rec.709 linear luminance in the annotated 64×64 target field;
historical nomination uses whole-context mean-RGB SD. These are different
measurements. Low absolute contrast in a dark exposure does not mean low
relative contrast everywhere. Individual sand grains, mud grains and bronze
microstructure are not asserted resolved merely because the source has them.

## Native examples

The strips show a whole-source thumbnail, native256 source crop and native256
area8 target. Only the thumbnail is resized. The linked local figures show an
unchanged native512 original crop beside the native64 target covering that same
physical field. Sources are ICC-managed to sRGB; targets use linear area2 from
the 4× cache then sRGB display. Exposure is ×1 throughout. These are clean-source
inspection views, without noisy observations or restored model outputs.

![Fine weak ceiling grid: source context, native source and native target](images/weak-photographic-targets-v1/brick-grid-context.png)

[Local source512/target64](images/weak-photographic-targets-v1/brick-grid-local.png) ·
[Source/ROI/display metadata](images/weak-photographic-targets-v1/brick-grid-context.json).
Source: [Diego Delso, Iglesia de San Pedro Los Francos](https://commons.wikimedia.org/wiki/File:Iglesia_de_San_Pedro_Los_Francos,_Calatayud,_Espa%C3%B1a,_2012-09-01,_DD_03.JPG),
[CC BY-SA3.0](https://creativecommons.org/licenses/by-sa/3.0/).

![Weak sea wavelets: source context, native source and native target](images/weak-photographic-targets-v1/sea-wavelets-context.png)

[Local source512/target64](images/weak-photographic-targets-v1/sea-wavelets-local.png) ·
[Source/ROI/display metadata](images/weak-photographic-targets-v1/sea-wavelets-context.json).
Source: [Diego Delso, Parque Natural da Arrábida](https://commons.wikimedia.org/wiki/File:Parque_Natural_da_Arr%C3%A1bida,_Set%C3%BAbal,_Portugal,_2012-05-11,_DD_13.JPG),
[CC BY-SA3.0](https://creativecommons.org/licenses/by-sa/3.0/).

![Faint plaster cracks: source context, native source and native target](images/weak-photographic-targets-v1/plaster-cracks-context.png)

[Local source512/target64](images/weak-photographic-targets-v1/plaster-cracks-local.png) ·
[Source/ROI/display metadata](images/weak-photographic-targets-v1/plaster-cracks-context.json).
Source: [Jacek Halicki, Kościół Stanisława Kostki](https://commons.wikimedia.org/wiki/File:2014_Ko%C5%9Bci%C3%B3%C5%82_Stanis%C5%82awa_Kostki_w_%C5%9Acinawce_Dolnej_12.JPG),
[CC BY-SA3.0 PL](https://creativecommons.org/licenses/by-sa/3.0/pl/deed.en).
Modifications for these examples: cropping, binning, context-thumbnail creation,
ICC/display and inspection-layout conversion. Full original attribution and
licensing for all fourteen sources remain in the catalogue.

## Actual data checks

All 28 unique candidate contexts and 56 native256 source/target cells were
actually viewed, followed by fourteen local source512/target64 pairs. This
counts twelve initial mixed-contrast candidates and sixteen measured candidates;
it is separate from the cumulative corpus-cleanup ledger. No training-source
membership changes result from this ROI review.

Original SHA1 and whole-cache SHA256 checks pass. Independent NumPy reconstruction
from the original eight selected source fields reproduces **393,216 bin4 uint16
values** and **98,304 native8 FP32 target values** exactly. The original six
catalogue objects and target hashes are unchanged; manifest binding is exact.
Local64 annotations describe inspected detail and are ignored by the trainer.

The actual clean-data reader exercises all fourteen regions through geometry
before final area2 and existing contrast attenuation at native256. Four ordinary
and two procedural samples match reused hashes from the preceding frozen-reader
check. All **20 outputs / 3,932,160 FP32 values** are finite. No excluded or
held-out cache opens; Python/NumPy/Torch global RNG remains unchanged and CUDA
stays uninitialized. No neural forward, noise observation, RAW decode or optimizer
update occurs. These are metadata-selected samples, not a training schedule.

The preparation receipt preserves its earlier reader-pending status; the
separate completed reader receipt records the subsequent check. The initial
local-view helper failed at import before pixel work; its source/log remain
preserved, and the corrected helper completed once. Reader success establishes
data readiness, with restoration quality still unmeasured.
