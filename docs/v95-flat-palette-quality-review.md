# Wider flat colors from V95: quality review in progress

The V97 endpoint shows a visible green/olive cast on the warm fabric in one preselected native photo. All four joint models still lose much of its fine suspension-line detail at this noise level. **V43 remains the working reference.** The complete fresh FP32 evaluation is running; these are early qualitative observations, with no aggregate quality result yet.

V96 and V97 completed 4,000 matched updates from final V95 EMA, preserving the original V43 architecture, curated 88,484-source corpus and the recipe with zero optical blur and more weak detail. Only colored smooth-field palette span differs: 0 versus 8 stops. Final 4k EMAs are primary; validation-best checkpoints remain diagnostic. See the [training plan and audits](v95-flat-palette-quality-plan.md).

## Fixed example scores

These are individual evaluation tiles, without a pooled mean or confidence
interval. Values are sRGB PSNR in dB for RGGB, exposure 1, over the native
240×240 area after the 8-pixel evaluation border. The displayed native crops
below use the smaller ROI [48,48,160,160]. The complete panel and its final
state/input/reference checks are still pending.

| Source | Condition | V43 | V95 | V96 | V97 |
| --- | --- | ---: | ---: | ---: | ---: |
| Fabric | ADC-only | 28.673 | 23.300 | 21.280 | 21.420 |
| Fabric | ISO100 prior | 26.873 | 21.719 | 20.982 | 19.522 |
| Fabric | ISO12800 prior | 40.570 | 32.389 | 31.267 | 24.354 |
| Building | ADC-only | 37.392 | 38.673 | 38.666 | 38.717 |
| Building | ISO100 prior | 39.267 | 40.404 | 40.518 | 40.535 |
| Building | ISO12800 prior | 35.394 | 35.842 | 35.865 | 35.869 |

The fabric regression also affects V95 and V96. At ISO12800, its chroma MAE is
0.003802 / 0.012539 / 0.013466 / 0.036038 for V43/V95/V96/V97. The building
instead improves modestly. Lower-noise fabric scores also worsen; the queued
native views will help inspect that behavior. These two fixed sources do not
determine the result over all 427 photographs.

The [fixed-score audit](results/v95-palette-fixed-example-scores-v1.json)
freezes the complete first processing batch: 1,008 rows covering four sources,
nine methods, seven conditions and four CFAs. Its 224 shared V43/V95 cases
match all recorded metrics from the earlier completed FP32 study exactly.
No extra inference or partial-panel average is used here.

## Native photographic triplets

Noisy → restored → exact synthetic GT. Each panel is an unchanged native 160×160 crop from a fixed 256×256 evaluation tile at ROI [48,48,160,160], at the 8×-binned photographic evaluation resolution. Both sources were fixed before viewing the endpoints. All methods share RGGB, ISO12800-prior conditioning (shot 0.00256/read 2.62144e-5, exposure 1), white balance/matrix/seed and sRGB display exposure 1. PNG pixels are never resized. Each adjacent JSON records full source, checkpoint SHA256, conditioning and display metadata.

### V43

![V43: noisy, restored and exact synthetic GT — Paraglider fabric and fine lines](images/v95-flat-palette/crop-09daca8a7d6943a8.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-09daca8a7d6943a8.json).

![V43: noisy, restored and exact synthetic GT — Building and clouds](images/v95-flat-palette/crop-085432538346e7c9.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-085432538346e7c9.json).

### V95

![V95: noisy, restored and exact synthetic GT — Paraglider fabric and fine lines](images/v95-flat-palette/crop-8f7bc348ce081939.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-8f7bc348ce081939.json).

![V95: noisy, restored and exact synthetic GT — Building and clouds](images/v95-flat-palette/crop-00dd92d39a9244e1.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-00dd92d39a9244e1.json).

### V96

![V96: noisy, restored and exact synthetic GT — Paraglider fabric and fine lines](images/v95-flat-palette/crop-c746f497532b5cb4.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-c746f497532b5cb4.json).

![V96: noisy, restored and exact synthetic GT — Building and clouds](images/v95-flat-palette/crop-f6b71053a64780db.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-f6b71053a64780db.json).

### V97

![V97: noisy, restored and exact synthetic GT — Paraglider fabric and fine lines](images/v95-flat-palette/crop-7b24445a5eb68506.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-7b24445a5eb68506.json).

![V97: noisy, restored and exact synthetic GT — Building and clouds](images/v95-flat-palette/crop-b728114ba3debcb1.png)

[Source/ROI/checkpoint/noise/display receipt](images/v95-flat-palette/crop-b728114ba3debcb1.json).

Source: [File:CH.VD.Villeneuve 2007-08-25 Vertigo-Swiss-Riviera 2392 3x2-R 4K.jpg](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg), Roy Egloff, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0). Modified through binning, crop, simulated noise and restoration.

Source: [File:Vancouver (BC, Canada), Coal Harbour Seaside Park, Blick in den Himmel -- 2022 -- 2158.jpg](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg), Dietmar Rabich, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0). Modified through binning, crop, simulated noise and restoration.

## Remaining review

The two photo examples do not establish a general winner. The full suite of 427 photos and 16 procedural sources, known/unseen measured-CFA panels, carrier/flat/color grids and standing GFX sky/building/foliage/fence/highlights remain pending. Real paired/AHD or separate ISO100 GFX references are not exact GT. All primary means and uncertainty, numeric audits and remaining actual native views must be recorded before a quality decision. Speed work stays deferred.

Additional ADC-only and ISO100 native views of the same fixed photos are queued
to check weak detail at lower noise. An ISO12800 repeat will check consistency
with the full suite. The four-source processing batch, checkpoints, RGGB/ROI,
calibration, seed and display settings stay fixed. Its controller waits for all
seven full-evaluation stages and their owners to exit. Fourteen protocol and
dependency tests pass, and an actual wait with no model worker is observed.
The [preparation receipt](results/v95-palette-native-photo-conditions-preparation-v1.json)
records these checks; the additional inference and native review are pending.

[Native viewing and publication receipt](results/v95-palette-first-native-photo-review-v1.json) · [Completed training and full evaluation launch](results/v95-palette-completed-training-and-evaluation-launch-v1.json).
