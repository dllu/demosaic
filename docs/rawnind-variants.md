# Current RawNIND reference variants

**The released pre-upsampled RawNIND is a stronger tested comparator than the
half-resolution variant used in our earlier reports.** It improves all 12
checked photographic cases and eight of nine development scene means. V104
still retains substantially more synthetic-photo detail, but its measured
real-camera means are close to this stronger reference. Broad real-camera
superiority remains unproven.

[Complete executions, independent audits and native evidence](results/rawnind-preupsample-current-v1.json).
Historical RawNIND scores retain their original half-resolution checkpoint;
the four-source photographic pilot below does not replace its full427 results.

## Matched observations and scores

Both references use the authors' original UtNet2, four packed Bayer planes,
32 starting channels and LeakyReLU. The half-resolution network upsamples at
its PixelShuffle output head. The alternative bilinearly upsamples the four
input planes before the CNN and uses a three-channel output head. Different
weights and training histories mean this is not an isolated architecture ablation.

Four previously selected material sources, original 240-pixel interiors,
three original noise draws/conditions, rendered sRGB PSNR:

| Condition | V104 | RawNIND half | RawNIND pre-upsampled |
| --- | ---: | ---: | ---: |
| ADC-only | 39.49290 | 27.60011 | 28.13487 |
| ISO100 prior | 40.80494 | 27.59567 | 28.12808 |
| ISO12800 prior | 33.49300 | 27.11000 | 27.59760 |

The alternative gains about .49–.53 dB over the half-resolution model, with
all 12 cases improving. V104 also beats the alternative in all 12. This is a
four-source material diagnostic, not a new 427-photo/seven-condition mean.

The **complete** original camera development panels use 72 known-scene crops
and 90 unseen-scene crops, 448-pixel scoring interiors, measured registered
low-ISO CFA references and source-balanced means:

| Method | Known4 CFA PSNR | Unseen5 CFA PSNR |
| --- | ---: | ---: |
| V102 | 54.23709 | 53.97177 |
| V104 | 54.26606 | 53.91700 |
| RawNIND half | 54.08474 | 53.76822 |
| RawNIND pre-upsampled | 54.26068 | 53.86528 |

Pre-upsampled minus half is **+.17594 dB** on known scenes, source-bootstrap
95% interval [+.11324,+.23672], improving 4/4 scenes. On unseen scenes it is
**+.09707 dB**, interval [+.00655,+.17382], improving 4/5; top_of_Expedit declines
.07039 dB. V104 minus the alternative is only +.00539/+.05172 dB on the two
panels, with intervals [−.40295,+.43126]/[−.29569,+.34782] spanning zero.
These intervals describe this fixed small source set, not training-seed uncertainty.

“Unseen” means held out from **our** training. External-model training membership
and overlap remain unproven. Neither these means nor this source set establish
a broad real-camera winner or SOTA result. The protected 16-scene reserve
remains unscored.

## Native photographic triplets

Noisy Malvar → **RawNIND pre-upsampled** → exact synthetic GT. Each panel is an
unchanged 160×160 crop at [48,48,160,160] inside its original native 256 context.
The ISO12800 physical shot/read coefficients, source/cache coordinates, WB,
camera matrix and common display exposure ×1 remain identical across methods.
The reference is exact for the declared synthetic observation. PNGs are RGB8
previews; scores use the unquantized float outputs.

![Pre-upsampled RawNIND bark: noisy, restored and exact synthetic GT](images/rawnind-preupsample-current/photo/crop-e659f83c17df7574.png)

![Pre-upsampled RawNIND fur: noisy, restored and exact synthetic GT](images/rawnind-preupsample-current/photo/crop-e5936d48a18f1ff1.png)

[V104 and both RawNIND variants, native comparison](images/rawnind-preupsample-current/photo/comparison.png) ·
[Source/ROI/checkpoint/noise/display and license metadata](images/rawnind-preupsample-current/photo/manifest.json).
Bark derives from Derek Ramsey (CC BY-SA 2.5), fur from Korall (CC BY 3.0);
binning, simulated noise, restoration and cropping are recorded modifications.

The alternative improves bark contours and fur modestly over the half-resolution
model. Both remain visibly softer than V104 on these exact-target examples;
V104 itself still misses some fine hairs and bark texture.

## Real captures

[All six standing GFX regions](images/rawnind-preupsample-current/gfx/comparison.png)
compare noisy Malvar, V104 and both RawNIND variants with the independent
DSCF3880 ISO100 reference. These are **512-pixel context restorations**, not new
102MP outputs. Each displayed cell is native 160, with common +2EV display.
The reference differs in aperture, exposure, motion and time and is **not GT**.
[GFX source/ROI/noise/display metadata](images/rawnind-preupsample-current/gfx/manifest.json).

V104 retains more regular mesh and building edges. The alternative is slightly
less coarse than half around some sign/rail structures, but foliage remains
soft. Saturated-light differences are also limited by clipping in this shared
display. These views do not establish a broad real-photo ordering.

The [two adverse Canon EOS M100 fields](images/rawnind-preupsample-current/camera/comparison.png)
retain the source and ROI selection made before evaluating the new variant.
Both RawNIND variants are smoother and score higher than V104 on those
specifically selected dark crops. Pre-upsampled versus half is mixed there:
58.98999 versus 58.92127 dB on Coulicoco, 62.07481 versus 62.08642 on top_of_Expedit.
The AHD display reference is auxiliary, **not exact RGB GT**.
[Camera source/ROI/checkpoint/display records](images/rawnind-preupsample-current/camera/manifest.json).

## Checkpoints and verification

The [authors' source and weight terms](https://github.com/trougnouf/rawnind_jddc/tree/e80fb7b14dc440bba38c01f312fd3cc02deb566c)
and [model definitions](https://github.com/trougnouf/rawnind_jddc/blob/e80fb7b14dc440bba38c01f312fd3cc02deb566c/src/rawnind/config/graph_denoise_models_definitions.yaml)
are pinned. Source is GPL-3.0; weights are offered under GPL-3.0 and CC BY 4.0.
The alternative's exact file ID is verified through the model-folder hierarchy
linked by the author README. Publisher arguments confirm preupsample=true,
four inputs, width 32, disabled transfer function and output-gain matching.

| Reference | Released iteration | Checkpoint SHA256 |
| --- | ---: | --- |
| Half | 4,350,000 | `c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0` |
| Pre-upsampled | 4,320,000 | `3d8d5fab966f790f4adbaf1786ca1ee81cb027d9cd45220787247b0af99fd814` |

The separately cached alternative is
`/mnt/external/demosaic/references/rawnind-preupsample-20261023-v1/utnet2-bayer-preupsample.pt`.
Its SHA256 pins the observed downloaded bytes; the provider-returned
31,057,675-byte size is verified. It is not a separately published SHA256 claim.
All 46 tensors load strictly, with 7,760,451 parameters and no random fallback.

Both variants preserve signed input samples, use recorded publisher global-ADC
normalization and fit gains only to the noisy CFA channels. Neither sees the
clean reference or consumes an explicit shot/read prior. The half model's four
pilot camera outputs replay earlier floats exactly; all 162 full-panel CPU
controls agree with the previous CUDA primary PSNR within .0000496 dB.
Four-CFA native 64 checks have identical canonical network inputs, repeated
outputs are exact and inverse-flip differences stay below 1.8e-7.

The pilot and full panels contain 378 actual reference-network forwards, zero
new V104 forwards and no training updates or RAW decodes. Independent NumPy64
rebuilds 376 primary score rows, including overlapping pilot observations,
and checks 1,104 channel-gain normal equations. All 96 native panels reproduce
from saved floats; all 52 distinct board cells were actually viewed.
Source snapshots and existing machine evidence retain their bytes.

Current training and the V104 selector are unchanged. Retain this stronger
tested reference in additional quality comparisons while preserving historical
half-resolution scores. Other released variants, including width 48, remain
untested here; this is not an exhaustive ranking of the published variants.
