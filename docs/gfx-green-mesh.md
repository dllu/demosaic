# Fine green fence beside the red train

**This additional real-capture case exposes missing weak detail and sensitivity
to noise conditioning.** With the nominal ISO6400 prior, V112, V114, V115 Small
and V117 largely erase the fine green lattice while retaining broad rails.
A fixed profile from nearby DSCF3879 makes more diagonal mesh texture visible in
V114 and V115, but the fine lattice remains much weaker than the reference.
RawNIND pre-upsampled keeps more directional texture under the nominal prior,
without clearly recovering the reference lattice.
The ISO6400 camera JPEG has very faint mesh amid grain; the separate ISO100
capture makes the physical structure much clearer. This remains an adverse case;
the limited conditioning gain is not a new trained-model result.

The case pairs **DSCF3842 ISO6400** with **DSCF3835 ISO100**, taken 46 seconds
earlier. Both camera JPEGs are included.
The existing DSCF3879/3880 standing scene and its six regions remain in use.

[Fixed sources and coordinates](../configs/gfx-green-mesh-20231231.json) ·
[Native image metadata](images/gfx-green-mesh-20231231-v1/manifest.json) ·
[Completed native review and data checks](results/gfx-green-mesh-v1.json).

## Fixed nearby-capture profile

The same V114 and V115 checkpoints were each run once more on the stored 768px
RAW context with one unchanged **DSCF3879 ISO6400 input-only profile**. It was
already recorded on October 17, before this mesh case. No coefficient sweep or
reference/output fitting was performed. The nominal predictions are reused.

| Conditioning | Shot | Read variance |
| --- | ---: | ---: |
| Generic ISO6400 prior | .00128 | 6.5536e-6 |
| Fixed nearby DSCF3879 profile | .0014635775921166604 | 1.0715704128646712e-6 |

This changes the physical profile, including a higher shot term and lower read
term; it is not a uniform strength multiplier. All observed RAW values, WB,
matrix, CFA geometry, ROI/reference/JPEG pixels and checkpoint bytes are identical.
Only the coefficients and their variance map change. The latter's median ratio
to the nominal map is .6344 in this context.

The two **native 160px** rows below share **+4EV display**. Columns: ISO6400 camera
JPEG, noisy Malvar, V114 nominal, V114 nearby profile, independent ISO100 AHD,
ISO100 camera JPEG. Neither ISO100 column is exact GT.

![Left mesh: fixed V114 checkpoint with nominal and nearby-capture profiles](images/gfx-green-mesh-profile-transfer-v1/V114-fine-green-mesh-left-4EV.png)

![Right mesh: the same matched V114 operators](images/gfx-green-mesh-profile-transfer-v1/V114-fine-green-mesh-right-4EV.png)

Both V114 and V115 show more diagonal structure, especially in the right crop.
The mesh remains soft, weak and irregular; grain/detail ambiguity and the small
blue point remain. This is a useful qualitative improvement in conditioning,
without establishing accurate lattice recovery or broad model superiority.

V115 matched comparisons: [left](images/gfx-green-mesh-profile-transfer-v1/V115-fine-green-mesh-left-4EV.png) ·
[right](images/gfx-green-mesh-profile-transfer-v1/V115-fine-green-mesh-right-4EV.png).
Native noisy/denoised/independent-reference triplets:
[V114 left](images/gfx-green-mesh-profile-transfer-v1/triplets/crop-4d11d77a521a9cc0.png) ·
[right](images/gfx-green-mesh-profile-transfer-v1/triplets/crop-8bcc58b8b6da3dc8.png) ·
[V115 left](images/gfx-green-mesh-profile-transfer-v1/triplets/crop-cc155f6f0840d134.png) ·
[right](images/gfx-green-mesh-profile-transfer-v1/triplets/crop-abe369d2868bd951.png).

The archived full-image DSCF3842 Haar bins have median absolute relative variance
mismatch of 15.56% with the nominal prior and .98% with the fixed nearby profile.
An [ADC-floor correction](noise-calibration-fit-support.md) additionally allows
valid negative read-noise samples in the actual mesh context: accepted patches
rise 51→2,134. Their median mismatches are 69.38%/5.81%, respectively. These are
input-only consistency diagnostics, not known camera-noise errors. The context's
intensity span is only .004957, so it remains correctly rejected for separate
shot/read fitting. Texture, correlation and selection can bias these statistics;
the transferred profile is not dedicated flat/dark calibration.

[Prospective plan, execution, actual review and independent audit](results/gfx-green-mesh-profile-transfer-v1.json) ·
[Source/ROI/checkpoint/conditioning/display metadata](images/gfx-green-mesh-profile-transfer-v1/manifest.json).
Exactly two new root/DINO forwards were executed, CPU FP32, with zero new RAW
decodes, noisy observations or training. Rendering forbids neural module calls.
Independent NumPy display arithmetic reproduces all 24 board cells exactly;
all 12 triplet cells equal their board counterparts. No full-frame, speed or
pixelwise quality claim is made.

## Nominal-prior controls

Columns: ISO6400 camera JPEG, noisy Malvar, V112, V114, V115 Small, V117,
RawNIND pre-upsampled, independent ISO100 AHD, ISO100 camera JPEG. Each cell is
an unchanged **160×160 native crop**, with shared **+2EV display**. Camera JPEGs
have their own tone, sharpening, denoising and geometric processing. The ISO100
images are independent qualitative references, **not exact GT**. No pixelwise
quality score is computed.

![Two native green-mesh regions, all fixed methods and camera JPEG controls](images/gfx-green-mesh-20231231-v1/comparison-2EV.png)

V114 noisy/restored/independent-reference triplets at the same native coordinates:

![V114 left mesh, noisy and independent ISO100 reference](images/gfx-green-mesh-20231231-v1/V114-left.png)

![V114 right mesh, noisy and independent ISO100 reference](images/gfx-green-mesh-20231231-v1/V114-right.png)

[V112 left](images/gfx-green-mesh-20231231-v1/V112-left.png) ·
[right](images/gfx-green-mesh-20231231-v1/V112-right.png) ·
[Small left](images/gfx-green-mesh-20231231-v1/V115-left.png) ·
[right](images/gfx-green-mesh-20231231-v1/V115-right.png) ·
[V117 left](images/gfx-green-mesh-20231231-v1/V117-left.png) ·
[right](images/gfx-green-mesh-20231231-v1/V117-right.png).
The model differences are small here; the large gap to the independent
ISO100 lattice should not be mistaken for an aperture-matched scoring result.

The README examples use the same retained predictions with **+4EV display** to
show these dark regions more clearly. Every panel receives the same additional
linear display gain; neither noise conditioning nor restoration is recomputed.
Camera JPEGs are decoded from sRGB before that gain. Their original camera
rendering still differs from the RAW display pipeline.

![Brighter left mesh: camera JPEG, noisy Malvar, V112, V114 and ISO100 camera reference](images/gfx-green-mesh-20231231-v1/fine-green-mesh-left-4EV.png)

![Brighter right mesh with the same columns](images/gfx-green-mesh-20231231-v1/fine-green-mesh-right-4EV.png)

## Capture and protocol

| Capture | ISO | Aperture | Shutter | Local capture time |
| --- | ---: | ---: | --- | --- |
| DSCF3842 | 6400 | f/1.7 | 1/300s | 2023-12-31 17:07:56 |
| DSCF3835 | 100 | f/5.6 | 2.5s | 2023-12-31 17:07:10 |

Both use the GFX100S and GF55mmF1.7. The low-ISO exposure differs in aperture,
depth of field, motion and time. Original RAWs and camera JPEGs remain read-only;
the local cache avoids further source-drive reads. The earlier cached noisy
RAF is reused, with the reference RAF and both JPEGs cached under
`.cache/gfx-green-mesh-20231231/`.

The RAW context is `[600,6260,768,768]`. The two noisy RAW regions start at
`[806,6489]` and `[1026,6449]`; the independent RAW reference uses a one-pixel
left translation. JPEG field matching requires larger offsets: about 46 pixels
horizontally in this part of the frame. Input-only coarse area8 correlation
followed by native integer translation selects coordinates. Coarse binning is
only for registration analysis. The displayed pixels are never resized or warped;
residual lens/rendering differences remain.

The original nominal comparison gives all five RAW methods the same signed
black-subtracted/white-normalized observation, RGGB geometry, noisy-capture WB/matrix and nominal ISO6400 prior:
**shot .00128, read variance 6.5536e-6**. This is a disclosed generic sensor prior,
not measured camera calibration. The existing DSCF3842 input-only fit was
unreliable because of insufficient intensity span. Restoration parameters are
fixed before viewing outputs. The reference uses LibRaw AHD camera RGB calibrated
only to its own RAW capture.

The original five-method run is a **768px context comparison**, with one CPU
IEEE-FP32 forward for each of the five methods and four DINO forwards. It is separate
from the complete102MP standing-scene restorations. All predictions are retained
as FP32 arrays, and future checkpoint additions can reuse these controls without
new control inference. A retained-output integration check forbids model loading
and module calls while reproducing all ten triplets and the full board exactly.
V119 is still training and is not included yet.

Preparation saves decoded context intermediates before alignment. Its `--decoded`
option reuses those bound intermediates for alignment-only follow-ups without
RAW re-decoding. Executed sources, input bindings and experiment receipts remain
preserved with the saved predictions.

## Held-out status

DSCF3835 and DSCF3842 identifiers are blocked even without camera metadata.
Their RAW and JPEG hashes join the protected captures; the entire GFX100S
2023-12-31 family remains excluded. The three actual V119 input manifests contain
neither these capture filenames nor their source hashes. The new case changes
no training source, recipe, checkpoint or existing evaluation queue.
