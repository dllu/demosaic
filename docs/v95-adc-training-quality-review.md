# ADC-training study: fixed native examples, full evaluation pending

V43 remains the working reference. Both new final 4k endpoints still lose fine
fabric cords and shift its color in the fixed high-noise example below. The
building retains clean geometry, without a convincing new detail advantage.
These two examples do not establish the overall V99−V98 result: the full
427-photo/16-procedural evaluation and the camera, texture, color and GFX panels
are still running or queued. No model is promoted.

V98 and V99 keep V43's learned architecture and continue from final V95 EMA
for 4,000 updates, with the same larger curated corpus, zero-PSF/weak-detail
recipe, seed 58 and shared LR 2e-6. V99 trains through the existing ADC sample
projection; V98 does not. Both use projected inference in the primary
comparison. Positive-noise priors, including these ISO12800 examples, bypass
that projection. Final 4k EMAs remain primary; validation-best states remain
diagnostic. See the [prospective plan](v95-adc-training-plan.md) and
[completed training audits/actual launches](results/v95-adc-training-complete-and-evaluation-launch-v1.json).

## Individual fixed examples

These are single-tile sRGB scores, without pooled means or confidence intervals.
RGGB, ISO12800-prior shot .00256/read .0000262144, exposure1. Scoring uses the
native 240×240 area after an 8-pixel border on the 256×256 tile; the displayed
native 160×160 crop is the smaller ROI [48,48,160,160]. Sources were fixed before
viewing the endpoints. Full-panel source/condition statistics remain pending.

| Model | Fabric PSNR, dB | Fabric chroma MAE | Building PSNR, dB |
| --- | ---: | ---: | ---: |
| V43 | 40.57026 | .003802 | 35.39359 |
| V95 | 32.38894 | .012539 | 35.84219 |
| V98 projected control | 30.43732 | .016694 | 35.84770 |
| V99 projected | 29.84932 | .017957 | 35.85223 |

V99 is 0.58800 dB below the projected control on this fabric tile, while the
building changes by only +0.00453 dB. The fabric issue already affects V95 and
becomes worse here. V43 is closer in broad fabric color, although it also loses
fine cords. RawNIND retains broad fabric color better than the later endpoints
in these views, but substantially softens the building's edges and windows.
Neither selected scene determines a broad winner.

The [fixed-example observation](results/v95-adc-fixed-native-photo-observation-v1.json)
freezes the first 1,008 case rows: four predeclared sources, nine methods, seven
conditions and four CFAs. All 784 shared reference cases, 6,272 metric fields
including nulls and eight shared preview triplets match the earlier completed
evaluation exactly. All 12 preselected triplets were represented in 16 actually
viewed native cells. This is a saved-data snapshot from the unfinished panel;
complete worker invariants and full quality review remain separate.

## Native 100% triplets

Noisy Malvar → restored → exact synthetic GT. Each panel is an unchanged native
160×160 crop at the 8×-binned evaluation resolution, with shared coordinates,
noise draws, WB [2,1,1.5], original matrix, 16-bit ADC with black level .03 and
sRGB display exposure 1. Crop pixels are never resized. Adjacent JSONs record full source,
checkpoint SHA256, ROI, conditioning and display metadata. PNGs are 8-bit sRGB
previews; scores use unquantized FP32 output. These are synthetic
observations of binned photographs; the standing real GFX scene remains a
separate qualitative test with a nonexact low-ISO reference.

### V98 projected control

![V98: noisy, restored and exact synthetic GT — fabric](images/v95-adc-training/crop-0f452518b631009f.png)

[Fabric source/ROI/checkpoint/noise/display metadata](images/v95-adc-training/crop-0f452518b631009f.json).

![V98: noisy, restored and exact synthetic GT — building](images/v95-adc-training/crop-f6c5338a17f027ff.png)

[Building source/ROI/checkpoint/noise/display metadata](images/v95-adc-training/crop-f6c5338a17f027ff.json).

### V99 projected

![V99: noisy, restored and exact synthetic GT — fabric](images/v95-adc-training/crop-f1ffca5ecb599f55.png)

[Fabric source/ROI/checkpoint/noise/display metadata](images/v95-adc-training/crop-f1ffca5ecb599f55.json).

![V99: noisy, restored and exact synthetic GT — building](images/v95-adc-training/crop-c35a0135145fdcdb.png)

[Building source/ROI/checkpoint/noise/display metadata](images/v95-adc-training/crop-c35a0135145fdcdb.json).

The [previous review](v95-flat-palette-quality-review.md) retains matching
V43/V95 crops and RawNIND context. The current full suite and queued
ADC/ISO100/ISO12800 diagnostic still require independent numeric closure and
actual native/GFX inspection. V43 stays the reference pending that review;
speed work remains deferred.

Photographic sources: [Roy Egloff](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg)
and [Dietmar Rabich](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by binning,
crop, simulated noise, restoration and rendering. These previews retain that license.
