# V111 final20k: early material gains and real GFX comparison

**V111 improves PSNR, SSIM, chroma error and gradient error on all twelve fixed
material cases over V104.** It is a useful new detail candidate in the same
DRUNet RGB / frozen DINOv3 ConvNeXt-Tiny family. Native low-noise bark and
canopy improve slightly; high-noise feather/hair detail and real GFX foliage
remain soft. The full photographic and camera comparison will follow V112's
matched training run, which is now live.

[Checkpoint, completed training boundary, independent audits and all native evidence](results/v111-final20000-early-quality-v1.json).
This report covers four selected sources and six real contexts. It does not
replace V104's completed full427, camera, color or weak-carrier results.

## Fixed material observations

Four source IDs absent from the actual 90,864-source training cohort; original
native256 inputs, RGGB, 240-pixel scoring interiors and unchanged noise draws.
These contexts were selected from clean images before inspecting these outputs.
They include mixed contrast and fine detail rather than globally faint images.

| Condition | V104 PSNR | V111 PSNR | Change, dB |
| --- | ---: | ---: | ---: |
| ADC-only | 39.49290 | 39.74670 | +.25379 |
| ISO100 prior | 40.80494 | 40.90464 | +.09971 |
| ISO12800 prior | 33.49300 | 33.51175 | +.01875 |

All twelve cases improve in each of PSNR, SSIM, chroma MAE and gradient MAE.
The PSNR gain ranges .01336–.33945 dB. These are descriptive results from four
selected sources, without a full-photo or training-seed uncertainty claim.
V104's exact retained float outputs are reused; no baseline inference is repeated.

Noisy Malvar → **V111 final20k** → exact synthetic GT. Each panel is native
160×160 at [48,48,160,160] within its original native256 context. Both use
ISO100-prior shot=.00002/read variance=.0000000016, WB=[2,1,1.5], the original
shared camera matrix and display exposure ×1. The stored observation hashes
bind the actual WB/matrix and sensor samples; crop pixels are never resized.

![V111 bark: noisy, restored and exact synthetic GT](images/v111-early-material/iso100-prior/crop-5c9cfe7a56e7eadf.png)

![V111 canopy: noisy, restored and exact synthetic GT](images/v111-early-material/iso100-prior/crop-f8f123bdd99f51b9.png)

| Source | 8× cache context xywh | Attribution |
| --- | --- | --- |
| Bark, `0ae232278265…` | [104,38,256,256] | Derek Ramsey, [CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/) |
| Canopy, `212ae12913ef…` | [133,67,256,256] | Grendelkhan, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

The manifests retain full Commons page URLs, authors and source hashes.
Modifications are binning, cropping, synthetic noise and restoration.

[ISO100 V104/V111 board and eight triplets](images/v111-early-material/iso100-prior/comparison.png)
([metadata](images/v111-early-material/iso100-prior/manifest.json)) ·
[ADC-only board](images/v111-early-material/adc-only/comparison.png)
([metadata](images/v111-early-material/adc-only/manifest.json)) ·
[ISO12800 board](images/v111-early-material/iso12800-prior/comparison.png)
([metadata](images/v111-early-material/iso12800-prior/manifest.json)).

All 48 board cells were viewed at native resolution. Low-noise bark grain and
canopy separation improve modestly. Fine white feathers and hairs remain
smoothed, especially at high noise; the numerical gains do not imply restored
fine structure everywhere.

## Standing GFX100S test

![Six GFX regions: noisy, V104, V111, stronger RawNIND pre-upsampled and separate ISO100 reference](images/v111-early-gfx/comparison.png)

The original DSCF3879 ISO6400 and DSCF3880 ISO100 pair, all six fixed
sky/building/foliage/fence/sign/platform regions, common +2EV display and native
160-pixel crops are retained. These are **512-pixel context restorations**;
V111 has no new complete102MP export yet. The ISO100 f/5.6 capture differs in
aperture, exposure, motion and time; it is a qualitative reference, **not GT**
or a pixelwise scoring target. [All eighteen triplets and metadata](images/v111-early-gfx/manifest.json).

V111 and V104 look close. Both retain coherent mesh and building edges relative
to the stronger pre-upsampled RawNIND reference. Sky remains smooth; fine
foliage and saturated-light structure remain soft. Shared clipping also limits
sign comparisons. All thirty cells were viewed; this does not show a decisive
new real-photo gain or establish broad superiority over RawNIND.

## Training, verification and use

V111 completed its original 20,000 updates from all 91 original V104 EMA tensors,
preserving learned fusion gates and the default reconstruction epsilon .001.
Fresh AdamW/EMA, seed62, B16/native256/BF16, LR1e-5/warmup200, zero optical PSFs,
weak textures, photographic contrast attenuation, six reviewed ROIs and
native128/paired32 remain as declared. Its 90,864-source corpus removes eight
more targets relative to V104. Extra updates, seed and cohort change together;
this does not isolate the cleaning effect or test the smaller loss scale.

All91 final model/EMA tensors and89 Adam states are finite at step20000.
The original worker exited, its controller adopted the completed receipt and
the actual source/manifest snapshot verifies. V112 starts from the same V104
EMA at epsilon .0003; its first input, loss and gradient replay its CUDA
preflight exactly. The two final endpoints will supply the matched loss test.

The read-only candidate checkpoint is
`/mnt/external/demosaic/models/v111-final20000.pt`, SHA256
`97ab9ca5f1f182ff42a4245c630bba810607a3d13b61cf8aae5842192a18da15`.
It works with the existing inference commands. V104 remains the broadly
evaluated working default while V111's full photo/camera/color/detail results
are pending; the new material gains and comparisons are available now.

The early reviews make eighteen V111 CPU FP32 forwards: twelve native256
material inputs and six native512 GFX contexts, with zero new other-model
inference, training or RAW decoding. Independent NumPy64 rebuilds24 paired
score rows for linear/sRGB PSNR and chroma/gradient MAE; maximum PSNR difference
is under .000004dB. SSIM/shadow/highlight values retain their original implementation.
All126 native panels reproduce exactly from saved floats, and all78 distinct
board cells were actually viewed. The audit preflight caught a missing board
helper before execution; the failed attempt is retained and a separately pinned
helper passes the corrected replay. Active training and original queues retain
their frozen bytes. Full panels, complete exports and the protected test reserve
are outside this early report; no speed or SOTA claim follows.
