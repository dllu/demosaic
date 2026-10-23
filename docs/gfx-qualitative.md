# GFX100S qualitative comparisons

**V102 final20k is the current quality baseline.** The latest gallery compares
complete102MP outputs for V101,V102,V103 and RawNIND on the standing
DSCF3879/DSCF3880 scene. The learned results remain close: fence strands and
building rails are more coherent than RawNIND, while fine foliage and saturated
sign structure still need work. [Completed model comparison](v102-v103-quality-review.md).

V104 completed 20k and improves the [selected material cases](heldout-detail.md).
Its complete 102MP exports follow the active quality evaluation. Current GFX
images below retain the completed V101/V102/V103 comparison.

## Current complete full-frame comparisons

![Six native GFX regions: noisy,V101,V102,V103,RawNIND and independent ISO100 reference](images/current-gfx-v102-v103-fullframe/gfx-comparison.png)

Columns: noisy Malvar,V101,**V102**,V103,RawNIND with input-only per-CFA-channel
gain,separate ISO100 f/5.6 reference. Each cell is **160×160 native sensor
pixels**, never resized. Open the original at100%; browsers may fit the board
to the window. Crops come from complete101.996MP blended IEEE FP32 restorations,
with tile512/overlap64/B4, before RGB16 encoding. All36 cells were actually viewed;
shared noisy/reference pixels match exactly across methods.

The last column is a separately captured, independently demosaiced qualitative
reference, **not GT**. Aperture,motion,LED scan and exposure differ. No pixelwise
quality scores are computed against it. Shared conditioning is
shot`.0014635775921166604`,read variance`1.0715704128646712e-6`,display×4(+2EV),
with the noisy capture's WB/matrix. PNGs are RGB8 sRGB previews; restored contexts
are FP32. [All24 triplets and source/ROI/checkpoint/noise/display metadata](images/current-gfx-v102-v103-fullframe/manifest.json).

![V102 full-frame foliage triplet](images/current-gfx-v102-v103-fullframe/V102-foliage.png)

![V102 full-frame chain-link-fence triplet](images/current-gfx-v102-v103-fullframe/V102-chain-link-fence.png)

The foliage remains soft in all three learned models. Fence geometry is more
continuous than RawNIND; blue/neon and illuminated edges still become rounded
or filled. The low-ISO capture has different optical detail and is not a
pixelwise scoring target. Four resized full-frame overviews were also viewed;
scene structure is coherent, but those overviews cannot establish native detail.

All eight RGB16 linear/sRGB TIFFs reopen as8746×11662×3,uint16,16bits/channel,
with complete-file hashes independently verified. The original writer also
checks sampled decoded rows against supplied floats; that is an export-path
check, not a whole-image learned-precision bound.

| Method | Full-frame inference/blending, seconds | Peak CUDA allocation, GB |
| --- | ---: | ---: |
| V101 | 199.51 | 3.61 |
| **V102** | **202.31** | **3.61** |
| V103 | 199.67 | 3.61 |
| RawNIND channel | 17.46 | 2.01 |

Settings: IEEE FP32,tile512/overlap64/B4,520 tiles,channels-last. These are
shared-machine observations excluding RAW decoding,model loading and writes.
They do not meet100MP/10s; quality remains the priority.
Artifacts:`/mnt/external/demosaic/v101-detail-diversity-fullframe-20261022-v1/`.
The controller and worker exited successfully.
[Completion,native/overview viewing and independent TIFF audit](results/v102-v103-quality-complete-v1.json).

## Other useful comparisons

The [V102 fixed5k/final20k CPU512-context comparison](images/current-gfx-v102-final/gfx-comparison.png)
([metadata](images/current-gfx-v102-final/manifest.json),
[exact parent replay and report corrections](results/V102-final20000-detail-GFX-CPU-v1.json))
is separate from full-frame blending. Its final20k material-panel gain remains
in the [natural-detail guide](heldout-detail.md).
<a id="v102-at-5000-updates"></a>
<a id="v102-at-5000-and-20000-updates"></a>

The earlier [V84/V100/V101 complete-frame gallery](images/current-gfx-fullframe/gfx-comparison.png)
([original receipt](results/gfx-V84-V100-V101-fullframe-v1.json)) retains its
168.47/168.21/168.05s timings and original pixels; the new table measures a
separate run. [Older CPU contexts](images/current-gfx/gfx-comparison.png) and
[V43/V84/V95](images/current-quality/gfx-comparison.png) remain useful evidence.
The latter's single V95 noisy-sky channel differs by1RGB8 level, as recorded
in its receipt; current pixels are never adjusted for presentation.

The [fixed-V101 conditioning study](noise-conditioning.md#real-gfx-contexts)
compares .50/.75/1.00/1.25× variance on the same six cached512 contexts. Lower
strengths retain more texture and grain; the calibrated1× default is unchanged.
The [Q2,Sony a7RII and GFX50R comparison](cross-camera-qualitative.md) adds six
low-ISO regions for V100/V102/V103 without a clean reference. The
[linear DNG/JPEG exporter](dng-export.md) and optional Bayer hot-pixel repair
are merged; repair is explicit and was off in these comparisons.

## Capture and crop protocol

DSCF3879 ISO 6400 and DSCF3880 ISO 100 are cached in
`.cache/gfx-qualitative-20231231/` (230MiB). The
[cache receipt](results/gfx-3879-3880-cache.json) records original/cache paths,
matching SHA256 hashes and source metadata. Subsequent testing reads the local
cache. Originals remain read-only; the scene and its siblings stay outside
training. Private RAWs and full-resolution renders stay outside Git.

Both captures are 11662×8746 Bayer images from the GFX100S and 55mm lens:

| Capture | Time | ISO | Aperture | Shutter |
| --- | --- | ---: | ---: | ---: |
| DSCF3879 | 17:13:27 | 6400 | f/1.7 | 1/240s |
| DSCF3880 | 17:17:05 | 100 | f/5.6 | 3s |

They are 3min38s apart. Aperture, depth of field, moving subjects, clouds and
LED scan differ. The sharper ISO 100 exposure is a qualitative reference,
**not exact GT**. No pixelwise PSNR/SSIM is computed against it.

The six regions were fixed from input/reference images before this comparison.
Only integer crop offsets are used: normalized-green correlation over a 512px
context, ±12px; featureless sky uses identical coordinates. Displayed pixels
are never warped, resized, sharpened or independently exposure-adjusted.

| Region | DSCF3879 top-left (x,y) | DSCF3880 top-left (x,y) |
| --- | --- | --- |
| Overcast sky | (5800,1400) | (5800,1400) |
| Building detail | (5790,2690) | (5791,2690) |
| Foliage | (8890,5570) | (8890,5570) |
| Chain-link fence | (2240,6000) | (2241,6000) |
| Colored neon sign | (9060,2050) | (9060,2050) |
| Illuminated platform boundary | (10320,4520) | (10321,4520) |

## Isolated blue features

Two blue features noticed in a V84 overview already occur in the noisy RAW.
The first also persists in the separate ISO 100 exposure; the second is absent
at those sensor coordinates in that later capture. Neither is created solely
by restoration. This pair does not distinguish scene lights, motion and sensor
causes, so the current processing retains them.

| Sensor (x,y) | ISO 6400 blue photosite | ISO 100 blue photosite |
| --- | ---: | ---: |
| (9065,5759) | .32675 | .32808 |
| (8991,5903) | .11302 | .00169 |

Values are black-subtracted/white-normalized sensor units. These posthoc input
diagnostics use two native 160×160 crops from each RAW, separately Malvar-demosaiced
with shared WB/matrix and +2 EV. The independent ISO 100 capture is not GT. They
are source observations, rather than independent model-selection cases.
[Source, ROI, pixels and display metadata](results/gfx-blue-feature-input-reference-v1.json).

![Native input/reference inspection of two blue features](images/gfx-blue-feature-input-reference.png)

## Reproduction

The source-frozen completed job is recorded under
`.cache/current-quality-20261022-v1/detail-diversity-fullframe-v1/`.
Its plan binds the fixed checkpoint hashes, source code, protected local RAW
cache and six ROIs. All seven preceding evaluation stages finished before
this GPU job began. Crops are extracted after complete-frame blending and
retain exact source/reference pixels. Preserve this evidence and use a fresh
output directory for any later model comparison.
