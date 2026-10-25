# Native camera development inputs

A supplementary development set now has **20 fixed256px regions from11 CC0
captures**, with240 shared synthetic-noise observations. It starts from
phase-aligned, low-ISO camera RGB rather than processed Commons RGB. Source WB
and color matrices remain attached to each region. **Prediction collection has
not launched; this is prepared data without a model-quality result.**
[Selection and protocol](../configs/native-camera-development-v1.json) ·
[Preparation and actual readback evidence](results/native-camera-development-inputs-v1.json).

The source references are **low-noise estimates, not exact noiseless GT**.
They retain reduced source noise and optical blur. Future scores describe
recovery of these fixed binned references under added noise. The full photo,
measured-camera and standing GFX comparisons continue to provide their own
quality evidence; this supplementary test does not replace them.

## Source and region selection

The existing128 native captures are all training data. We inspected29 other
cached public RAW previews that were withheld from training because of clipped
source regions. Twelve photographic candidates received native inspection:
39 unchanged160px reference crops across four pages. Eleven had suitable
256px contexts; the Nikon park capture had none under the declared rule and
was dropped. Twenty regions were selected before any model output on these
inputs was examined.

| Source file ID | Camera label | Selected regions |
| --- | --- | --- |
| 5002 | GFX50S II | Grass/root detail and a lower tree trunk |
| 1603 | LEICA M10 | Window/brickwork and lower-contrast mortar |
| 1797 | LEICA Q (Typ116) | Lily foliage and dark reeds |
| 1951 | LEICA SL (Typ601) | Two weathered wood-rail regions |
| 4160 | NIKON Z6_2 | Two leafless-woodland regions |
| 3235 | DC-G91 | Roof/window/balcony detail |
| 1504 | DMC-CM1 | Two masonry/grout regions |
| 3103 | DMC-TX1 | Trunk/roots and darker pond-bank detail |
| 2247 | DSC-RX10M4 | Fine tea-bush rows |
| 1535 | ILCA-99M2 | Tree foliage and a sky/field control |
| 5075 | ILCE-7RM3A | Stone-wall texture and sign lettering |

The source256 context and a mapped four-pixel guard at4× resolution contain
no cache channel value≥60000. This bounds clipping in the retained caches;
individual sensor pixels may have clipped before averaging. Both4×/8× caches
trim a border, so the coordinate map includes a one-cell4× offset. A linear-ramp
fixture checks the actual binning operators at12 ROIs/four Bayer layouts:
correct mapping is exact, while omitting the offset produces the predicted
.0029296875 displacement error.

Reference pixels are copied directly from the8× cache, with no geometry,
resize or camera/sRGB/inverse-camera round trip. The inference context is256px;
the fixed score/display interior is `[48,48,160,160]`. Some same-source regions
overlap. Aggregate repeats/CFAs/ROIs within source before equal-source means;
the20 regions and240 cases are not240 independent photographs.

## Source identity and protected data

The finite content screen covers all103,604 current Commons records, including
legacy exclusions/reserves. It reuses a private copy of the matching-algorithm
fingerprint cache and adds9,212 missing entries from verified cached bytes.
No threshold match is found; all36 nearest-correlation suggestions were actually
viewed and show different subjects/compositions.

The source audit reconciles all128 current native captures and154 unique clean
references in the83-ID paired set. Cached full-reference identity views cover
all but one small Nikon reference; that one cached NEF receives an identity-only
LibRaw render. All42 protected reference screens and the exact current cached
DSCF3879/3880 hashes verify. Original sources, admissions, training manifests
and V119's frozen execution remain unchanged.

These are held-out captures under source hashes and finite full/crop/orientation
screens. Camera models or unrecognized geographic places may overlap training;
the screen is not complete scene recognition. The GFX5002 grove, for example,
does not visibly match training4493's woodland-edge composition, but geographic
place identity is unknown. No protected-final model performance is consulted.

## Prepared observations and checks

| Setting | Value |
| --- | --- |
| Conditions | ADC-only, ISO100 prior, ISO12800 prior |
| Shot/read coefficients |0/0,2e-5/1.6e-9,.00256/.0000262144 |
| Meaning | Declared sensor priors, not measured profiles for these cameras |
| ADC / black level |16 bits /.03 |
| Sampling | Direct camera-RGB Bayer sampling; RGGB/BGGR/GRBG/GBRG |
| Randomness | CPU generator keyed by seed20261025, case, condition and CFA |
| Sharing |240 observations generated once and saved for every future method |

The [builder](../scripts/prepare_native_development.py) forbids neural Module
calls, leaves CUDA uninitialized and preserves global Python/NumPy/Torch RNG.
Actual readback verifies3,932,160 uint16 reference values exactly against source
slices, the same number of canonical FP32 values, and15,728,640 noisy plus
15,728,640 variance values. Independent variance arithmetic agrees exactly.
The actual native training loader rejects the development manifest.

Completed local inputs:
`.cache/current-quality-20261023-v1/native-camera-development-inputs-v1/manifest.json`.
Reuse these arrays for predictions and reports. To reproduce data preparation,
use a new output directory:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 .venv/bin/python \
  scripts/prepare_native_development.py configs/native-camera-development-v1.json \
  .cache/native-camera-development-copy-v1
```

## Native source-reference inspection

These unchanged160×160 cells are at8×-binned target resolution, with metadata
WB/matrix, exposure×1 and no resized pixels. They are source-reference
inspections, with no added noise or learned output in the PNGs.
[Source/ROI/display/license metadata](images/native-camera-development-v1/manifest.json).

![GFX50S II foreground grass and root reference estimate, native160](images/native-camera-development-v1/5002-fine-reference-native160.png)

![Leica M10 brick/mortar reference estimate, native160](images/native-camera-development-v1/1603-field-reference-native160.png)

![Leica SL weathered wood reference estimate, native160](images/native-camera-development-v1/1951-field-reference-native160.png)

Sources: per-file CC0 grants from the [RAW source catalogue](https://raw.pixls.us/),
with original URLs and metadata checksums in the selection. Modified by
phase-aligned binning, cropping and the shared display transform.

The next comparison can evaluate V119's final endpoint alongside useful
V114/V115/V117 options and the stronger released RawNIND reference after the
original review releases GPU ownership. These would be first predictions on
the new inputs. Useful completed progress continues to update current guides
as its full results and native review become available.
