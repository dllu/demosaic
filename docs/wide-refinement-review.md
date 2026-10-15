# Larger RGB correction branch

V16 increases the correction branch from width 24/four blocks (27,696 parameters)
to width 48/eight blocks (144,072). Original restoration/DINO weights remain
frozen at the same V11 step5000 initialization. Data proportions, losses and
learning rate match V15; model initialization consumes a different RNG sequence,
so this is a capacity trial rather than a matched data-sequence ablation.

The first 1000 steps improve both real development sets over V15 at step1000:

| Method | Known measured-CFA PSNR | Unseen measured-CFA PSNR | Known AHD SSIM | Unseen AHD SSIM |
| --- | ---: | ---: | ---: | ---: |
| V15 step1000 | 52.5264 | 52.1592 | 0.90558 | 0.87600 |
| V16 step1000 | 52.9210 | 52.6045 | 0.91375 | 0.88986 |
| V15 step5000 | 53.0998 | 52.8518 | 0.91754 | 0.89840 |
| V16 step5000 | 53.2747 | 53.0786 | 0.92152 | 0.90718 |
| RawNIND, publisher units, CFA-LS | 54.0686 | 53.5622 | 0.92881 | 0.91838 |

V16 completed 5000 steps. It gains 0.17490/0.22676 dB over V15 at the same step
count, with exploratory scene-bootstrap 95% intervals [0.04320,0.35989] and
[0.15510,0.29341]. Four/five development scenes provide limited generalization
evidence. Auxiliary RGB PSNR reaches 39.15836/37.65963. RawNIND still leads by
0.79394/0.48363 dB measured PSNR, and its GFX sky remains cleaner.

The full shared 427-photo synthetic suite gives **31.48800/0.923018** sRGB
PSNR/SSIM, versus V15's 31.44165/0.921748. Procedural 16-source PSNR/SSIM reaches
30.56577/0.922656, versus 30.49185/0.919789. The older V6 still has the stronger
synthetic photo PSNR. These gains do not establish state-of-the-art quality.
Protected test targets remain unused for model selection.

At the earlier step1000 review,
A predeclared 64-photo synthetic screen gives sRGB PSNR/SSIM 31.89746/0.922292,
versus V15 step1000 31.87841/0.921193 on the same inputs. Procedural eight-source
PSNR/SSIM is 29.10436/0.905848 versus 29.07705/0.904316. This screen is not the
complete 427-photo suite. Its first-review receipts remain archived separately.

Fixed 160×160 native crops from the known-camera report, same locations and
display settings as V15. Left: noisy Malvar; middle: V16 step5000; right: auxiliary
calibrated low-noise AHD reference, not exact RGB GT. Open the PNGs at 100%.

![Noisy, V16, AHD reference: plates](images/refiner-wide-v16-5k-plates.png)

![Noisy, V16, AHD reference: structure](images/refiner-wide-v16-5k-7d.png)

[Step5000 source/checkpoint/manifest hashes, exact crop settings and aggregate results](results/wide-refiner-v16-5k-review.json).
The [step1000 review](results/wide-refiner-v16-1k-review.json) remains archived.
Noise and missing fine structure remain visible. Exact synthetic-GT examples at
the same fixed native 160×160 locations are:

![Noisy, V16, exact synthetic GT: fabric](images/validation-fabric-v16.png)

![Noisy, V16, exact synthetic GT: building](images/validation-building-v16.png)

These are 100% at the 8×8-binned evaluation resolution; all methods use shared
display transforms. Full 102 MP RGB16/ICC-sRGB16 GFX outputs were also verified;
see [the native GFX comparison](gfx-qualitative.md).

The [residual-scale diagnostic](residual-scales.md) motivates a separate coarse
correction trial. Its first 1000 steps did not meaningfully improve quality and
are not promoted. Next, V18 jointly tunes restoration/fine correction while V19
continues fine-correction-only training, from identical V16 weights, seed 43,
data and LR 3e-5. Optional observation/target hashes verify sampled input equality.
DINO backbone parameters remain frozen in both. Their [matched first review](joint-tuning-review.md)
does not support promotion; both are continuing to the original step5000 review.

Sources: Benoit Brummer and Christophe De Vleeschouwer, *Raw Natural Image Noise
Dataset (2025)*, [dataset](https://doi.org/10.14428/DVN/DEQCIM),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), with additional
scene permissions retained locally (`7D-1`: Peter Wemmert, CC0). Modified by
registration, calibration, demosaicing/restoration, cropping and shared display.

Synthetic sources: Roy Egloff,
[Villeneuve Vertigo-Swiss-Riviera](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg),
and Dietmar Rabich,
[Vancouver Coal Harbour](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
CC BY-SA 4.0, modified by binning, crop, synthetic noise and restoration.
