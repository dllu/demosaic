# Wider flat colors from V95: primary-panel results

Neither V96 nor V97 establishes a photographic PSNR gain over V95. Most sources improve slightly, but substantial regressions on a few sources offset those gains. V97 also shows a visible green/olive cast on the warm fabric in one preselected native photo. **V43 remains the working reference.** All three primary panels are complete; weak-detail, color and GFX review continues.

V96 and V97 completed 4,000 matched updates from final V95 EMA, preserving the original V43 architecture, curated 88,484-source corpus and the recipe with zero optical blur and more weak detail. Only colored smooth-field palette span differs: 0 versus 8 stops. Final 4k EMAs are primary; validation-best checkpoints remain diagnostic. See the [training plan and audits](v95-flat-palette-quality-plan.md).

## Complete primary panels

Fresh IEEE FP32, identical observations and fixed checkpoint bytes. Photo means
balance 427 sources across seven conditions and four CFAs. Known/unseen camera
means balance 4/5 scenes over 72/90 crops and compare measured CFA samples.
The 16 procedural sources remain separate from photographic means.

| Model | Photo sRGB PSNR | Known CFA PSNR | Unseen CFA PSNR |
| --- | ---: | ---: | ---: |
| V43 | 34.89933 | 54.23334 | 53.80629 |
| V95 | 35.29553 | 54.33307 | 53.76990 |
| V96 | 35.27828 | 54.32564 | 53.76643 |
| V97 | 35.28321 | 54.32529 | 53.76365 |

| Contrast | Photo delta, 95% interval | Known delta, 95% interval | Unseen delta, 95% interval |
| --- | ---: | ---: | ---: |
| V96 minus V95 | −0.01725 [−0.05519, +0.01372] | −0.00743 [−0.02260, +0.00774] | −0.00347 [−0.03997, +0.03219] |
| V97 minus V95 | −0.01232 [−0.04718, +0.01788] | −0.00778 [−0.02797, +0.01241] | −0.00626 [−0.04127, +0.04183] |
| V97 minus V96 | +0.00492 [−0.01276, +0.02189] | −0.00035 [−0.00798, +0.01090] | −0.00279 [−0.02342, +0.01716] |

Intervals use 1,000 paired source/scene resamples, seed 42, and do not measure
training-seed uncertainty. The matched wider-palette contrast is uncertain.
V96's extra training alone also gives no established PSNR gain over V95.
Photographic SSIM rises slightly, from 0.960148 to 0.960290/0.960312, while
chroma MAE worsens from 0.007596 to 0.007649/0.007631 for V96/V97.

Source-level changes reveal the failure tail. These values average all 28
condition/CFA combinations within each photograph before taking deltas:

| Contrast | Sources with higher PSNR | Median delta | Worst delta |
| --- | ---: | ---: | ---: |
| V95 minus V43 | 400/427 | +0.47461 | −6.35319 |
| V96 minus V95 | 330/427 | +0.04068 | −3.98915 |
| V97 minus V95 | 336/427 | +0.04166 | −3.38332 |
| V97 minus V96 | 225/427 | +0.00091 | −1.82180 |

The [primary statistics and independent replay](results/v95-palette-primary-statistics-v1.json)
check all 111,636 photo/procedural records and 648/810 camera records.
All 25,132 shared V43/V95 cases match the earlier completed study exactly,
including 200,408 metric fields with nullable support. The maximum independent
summary discrepancy is below 1.5e-14. The receipt retains per-noise means,
all primary contrasts and source-delta quantiles.

All 24 saved camera triplets were represented in 32 actually viewed native
cells. The joint models look close in these four fixed ROIs, without a
convincing palette-specific detail gain. The [camera viewing record](results/v95-palette-native-camera-review-v1.json)
records the source boards and observations. AHD references retain grain and
interpolation artifacts and are not exact RGB GT.

## Fixed example scores

These are individual evaluation tiles, without a pooled mean or confidence
interval. Values are sRGB PSNR in dB for RGGB, exposure 1, over the native
240×240 area after the 8-pixel evaluation border. The displayed native crops
below use the smaller ROI [48,48,160,160]. The complete panel and its final
state/input/reference checks have passed; these two examples illustrate
behavior that an aggregate mean can obscure.

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

The primary means and native photo/camera views do not establish a general winner. Carrier/flat/color grids and standing GFX sky/building/foliage/fence/highlights remain pending. Real paired/AHD or separate ISO100 GFX references are not exact GT. Remaining numeric audits and actual native views are required before the complete quality decision. Speed work stays deferred.

Additional ADC-only and ISO100 native views of the same fixed photos are queued
to check weak detail at lower noise. An ISO12800 repeat will check consistency
with the full suite. The four-source processing batch, checkpoints, RGGB/ROI,
calibration, seed and display settings stay fixed. Its controller waits for all
seven full-evaluation stages and their owners to exit. Fourteen protocol and
dependency tests pass, and an actual wait with no model worker is observed.
The [preparation receipt](results/v95-palette-native-photo-conditions-preparation-v1.json)
records these checks; the additional inference and native review are pending.

[Native viewing and publication receipt](results/v95-palette-first-native-photo-review-v1.json) · [Completed training and full evaluation launch](results/v95-palette-completed-training-and-evaluation-launch-v1.json).
