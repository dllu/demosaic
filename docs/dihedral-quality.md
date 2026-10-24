# Optional eight-view restoration

**Eight-view V104 improves all twelve fixed material cases and both selected
adverse camera crops.** It uses the original V104 weights, averaging exact
rotations/reflections in linear camera RGB. Bark and canopy improve modestly;
high-noise fine detail and real dark-field blotches remain. This is an optional
inference policy requiring eight model evaluations per tile.

Add `--self-ensemble dihedral8` to `demosaic infer`, `demosaic benchmark`,
`demosaic quality` or
[`scripts/export_raw_dng.py`](../scripts/export_raw_dng.py). The ordinary default
is `none`. Output receipts record the policy and model views per tile. The
reported quality uses `--precision float32`; reduced-precision quality has not
been measured for this policy. The
full 102MP GFX export is queued after the original V111/V112 workflow; the
comparisons here use fixed 256/512-pixel contexts.

[Scores, sources, weights, independent audit and implementation checks](results/v104-dihedral8-pilot-v1.json).
The original final20k checkpoint is `/mnt/external/demosaic/models/v104-final20000.pt`,
SHA256 `8a3a7d94f2b1465cbdddbeec201fb37a2f69b12c74f9298527a94e3a7bbf6300`.
No weights, noise coefficients or target-dependent gains were fitted.

## Fixed photographic panel

Four previously selected, held-out sources, three conditions, RGGB, original
256-pixel observations and 240-pixel scoring interiors. All twelve sRGB PSNRs
improve; mean chroma and gradient errors fall in every condition.

| Condition | V104 single | V104 eight views | Change, dB |
| --- | ---: | ---: | ---: |
| ADC-only | 39.49290 | 40.06104 | +.56814 |
| ISO100 prior | 40.80493 | 41.09810 | +.29317 |
| ISO12800 prior | 33.49300 | 33.57486 | +.08187 |

These four-source means describe this fixed material panel, not the full 427-photo
photo panel, all four CFAs, or training-seed uncertainty. The separate
[V111 trained-model report](v111-early-quality.md) retains its own gains.

Noisy Malvar → **V104 eight views** → exact synthetic GT. Both examples use
160-pixel crops at ROI [48,48,160,160] within their original 256-pixel contexts, the
ISO100 prior (shot .00002/read variance .0000000016), WB=[2,1,1.5], the shared
matrix in the manifests and display exposure ×1. Pixels are never resized.

![Eight-view V104 bark: noisy, restored, exact GT](images/v104-dihedral8-pilot/iso100-prior/crop-71f9f046a82a8c7c.png)

![Eight-view V104 canopy: noisy, restored, exact GT](images/v104-dihedral8-pilot/iso100-prior/crop-070de1f76e8f392e.png)

[ISO100 before/after board and source/ROI/noise/display metadata](images/v104-dihedral8-pilot/iso100-prior/manifest.json) ·
[ADC board](images/v104-dihedral8-pilot/adc-only/comparison.png) ·
[ISO12800 board](images/v104-dihedral8-pilot/iso12800-prior/comparison.png).
Fine white feathers and hairs remain smoothed, especially at high noise.

## Adverse real-camera crops

The two original V104-adverse Canon M100 crops, original input-only noise
profiles and 448-pixel measured-CFA scoring interiors are unchanged.
Independently demosaiced AHD RGB is auxiliary, **not exact GT**.

| Selected crop | V104 single | V104 eight views | RawNIND pre-upsampled |
| --- | ---: | ---: | ---: |
| Coulicoco | 56.98928 | 57.30272 | 58.98999 |
| top_of_Expedit | 60.67192 | 60.93926 | 62.07481 |

![Original adverse fields: noisy, single view, eight views and auxiliary AHD](images/v104-dihedral8-pilot/camera/comparison.png)

Eight views gain .31344/.26734dB, but both remain below the stronger released
RawNIND reference. Broad colored blotches remain. These are two selected
crop results, not complete camera-panel or scene means.
[Source/ROI/conditioning/display metadata](images/v104-dihedral8-pilot/camera/manifest.json).
All cells are 160-pixel crops with shared +2EV. The RawNIND numbers reuse the earlier
[audited same-crop comparison](v111-early-quality.md#complete-development-camera-panels);
no new reference inference was run.

## Standing GFX scene

![GFX native contexts: noisy, single view, eight views and separate ISO100 reference](images/v104-dihedral8-pilot/gfx/comparison.png)

All six fixed sky/building/foliage/fence/sign/platform regions use native160
sensor-pixel crops from 512-pixel contexts and common +2EV display.
DSCF3879 ISO6400 is the input; DSCF3880 ISO100 f/5.6 is an independently
captured qualitative reference, **not GT**. Aperture, exposure and moving
subjects differ. Single/eight-view changes look small: fence/building geometry
remains coherent, while foliage and saturated-light detail remain soft.
[Complete crop and transform metadata](images/v104-dihedral8-pilot/gfx/manifest.json).
The [full-frame gallery](gfx-qualitative.md) retains the completed single-view
102MP comparisons until the queued eight-view export is actually reviewed.

## Implementation and verification

Full sensor mosaics, spatial variances and the 2×2 CFA color tile receive the
same exact rotations/reflections. WB/matrix and physical noise conditioning
retain their camera meanings. Each prediction returns to the original
coordinates, then receives an equal float64 mean before float32 tile blending
and RGB16 export. No interpolation, new noise draw or fitted correction occurs.
Only the current view and accumulated sum persist; eight full-image outputs
are not retained during tiled inference.

NumPy64 independently reconstructs all 20 saved means exactly and rebuilds
photo/camera PSNR, chroma and gradient scores; maximum PSNR discrepancy is
under .000004dB. All 20 identity views exactly replay the retained original
V104 floats. SSIM and masked highlight/shadow metrics retain their original
implementation. All 80 distinct native cells were actually viewed.

## Full comparison queued

The full comparison now uses the public photo, prepared-camera, texture and
color evaluators with `self_ensemble="dihedral8"`. Checkpoint labels and receipts
record the policy; reference methods keep their original single-view inference.
Color caches match the inference policy as well as the weights, so single-view
predictions cannot stand in for eight-view results.

| Panel | Averaged observations |
| --- | ---: |
| 427 photos + 16 procedural sources, 7 conditions × 4 CFAs | 12,404 |
| Known-camera crops | 72 |
| Unseen-camera crops | 90 |
| Weak carriers and neutral flats | 448 |
| Analytic colors | 1,176 |
| Total | 14,190 |

These require 113,520 per-image model-view evaluations. The frozen run retains
every averaged prediction and records input fingerprints, view hashes and an
independent NumPy64 reconstruction of each mean. The photographic observations
also replay the preserved single-view observation code exactly. Existing
single-view/reference results remain the controls.

The queue waits for the exact eight-view full-GFX process, which itself follows
the original V111/V112 matched workflow. It checks successful dependency results,
memory and disk reserves before starting. Independent metric checks and actual
native-crop review follow completion; this queue adds no measured quality result
yet. [Plan, CPU proof and launch receipt](results/v104-dihedral8-full-quality-queued-v1.json).

An independent score audit is also queued after the full evaluation. It
regenerates the original input fingerprints, rehashes saved means and rebuilds
photo PSNR/detail, measured-CFA, carrier/flat and analytic-color metrics in
NumPy64. Source-weighted changes against the original V104 results and scene
comparisons against the stronger RawNIND pre-upsampled reference use existing
control measurements. Neural-module calls are forbidden during the audit.
Full photo replay uses the original CUDA RNG after evaluation finishes.

Its actual CPU fixtures agree with saved PSNR within .000004dB and reproduce
their inputs exactly. The new context replay also reproduces all 112 existing
texture batches and recovers the published V104 photo/known/unseen means.
These verify arithmetic and joins using existing artifacts; the full eight-view
results and native review remain pending.
[Audit scope, proofs and exact process dependency](results/v104-dihedral8-audit-queued-v1.json).

Thirty-seven targeted operator tests pass, including single-view references,
measured-CFA scoring and cache-policy separation. Real-weight CPU engineering
checks complete 24 model/encoder forwards over two photo observations and one
camera crop; each streamed mean agrees exactly with the independent NumPy64
calculation. These small CPU fixtures verify execution, not full-panel quality.

The earlier pilot integration checks show that the production helper exactly
reproduces four genuine-weight pilot cases,
with 40 actual CPU forwards including tiled RGB16 write/read. A small actual
GB10/CPU 128-pixel check agrees within 1.79e-7 camera units, with identical rounded
PSNR. It overlaps training and provides no throughput measurement. Thirty-two
focused tests cover four CFA layouts, non-square/signed data, odd-sized tile
blending, native RGB16, CLI wiring and real DNG/hot-pixel/darktable export in
both policy modes.

The first geometry fixture omitted its intended above-white range; the first
renderer used a destination outside the frozen evaluator's output root; and
the first GPU validator failed to reset device-specific noise tables after
moving a previously used CPU model. Their sources/logs remain preserved.
Corrected checks pass without changing the pilot scores or model weights.

Full 427-photo, complete camera panels and full analytic color/weak-texture grids
are queued and remain unevaluated for this policy. The eight-view full 102MP
export is queued, so no full-frame speed or broad-superiority claim follows from these context
comparisons. V112's matched training continues separately.

Photo attribution: [Derek Ramsey, bark](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/);
[Serebit, snowy egret](https://commons.wikimedia.org/wiki/File:Snowy_egret_in_profile.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
[Grendelkhan, canopy](https://commons.wikimedia.org/wiki/File:Forest_covered_hills_on_Yakushima.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
[Korall, raccoon](https://commons.wikimedia.org/wiki/File:Racoon_clinging_to_a_tree.JPG),
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
Modifications: original 8× binning/cropping, synthetic noise, restoration and
shared display conversion.
