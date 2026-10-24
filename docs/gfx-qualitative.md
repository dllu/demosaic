# GFX100S qualitative comparisons

**V104 is the current positive-noise quality baseline.** The latest gallery
compares complete 102MP V102/V104/RawNIND-half outputs on DSCF3879/DSCF3880. The two
learned models remain close: fence strands and building rails are more coherent
than RawNIND, while fine foliage and saturated-sign structure remain soft.
[Completed V104 metrics and tradeoffs](v104-reviewed-corpus-quality.md).

## Current complete full-frame comparisons

![Six native GFX regions: noisy,V102,V104,RawNIND and independent ISO100 reference](images/gfx-v102-v104-fullframe/comparison.png)

Rows: noisy Malvar, V102, V104, RawNIND half with input-only CFA-channel gain,
independent ISO100 f/5.6 reference. Each cell is **160×160 native sensor pixels**,
never resized. Crops come from complete 101.996MP IEEE FP32 blended outputs,
with tile512/overlap64/B4, before RGB16 encoding. All 30 native cells were
viewed at original resolution; shared noisy/reference pixels match exactly.
Open the original PNG at 100%; a browser may fit it to the window.

The final row is a separately captured and independently demosaiced qualitative
reference, **not GT**. Aperture, motion, LED scan and exposure differ; it has no
pixelwise quality score. Shared conditioning is shot .0014635775921166604,
read variance 1.0715704128646712e-6, display ×4 (+2EV), using the noisy capture's
WB/matrix. PNGs are RGB8 previews of float output.
[All 18 triplets and source/ROI/checkpoint/noise/display metadata](images/gfx-v102-v104-fullframe/manifest.json).

![V104 full-frame foliage: noisy, restored and separate low-ISO reference](images/gfx-v102-v104-fullframe/V104-foliage.png)

![V104 full-frame fence: noisy, restored and separate low-ISO reference](images/gfx-v102-v104-fullframe/V104-chain-link-fence.png)

Foliage retains broad leaf shapes while losing fine surface detail. Fence
geometry is clearer than RawNIND; bright blue/neon and platform edges remain
rounded or filled. The separate f/5.6 capture has different optical detail.
Three resized full-frame overviews were also viewed: scene geometry is coherent,
while native detail must be assessed from the unchanged crops above.
[V102 overview](images/gfx-v102-v104-fullframe/V102-overview.png) ·
[V104 overview](images/gfx-v102-v104-fullframe/V104-overview.png) ·
[RawNIND overview](images/gfx-v102-v104-fullframe/RawNIND-overview.png).

All six linear/sRGB RGB16 TIFFs were completely rehashed and reopened as
8746×11662×3 uint16, 16 bits/channel. The original exporter also checked sampled
decoded rows against supplied floats; this is an export-path check rather than
a whole-image learned-precision bound.

| Method | Full-frame inference/blending, seconds | Peak CUDA allocation, GB |
| --- | ---: | ---: |
| V102 | 168.20 | 3.37 |
| V104 | 168.73 | 3.36 |
| RawNIND channel | 17.40 | 1.77 |

Settings: IEEE FP32, tile512/overlap64/B4, 520 tiles, channels-last. These
shared-machine observations exclude RAW decoding, model loading and writes.
They do not meet 100MP/10s; no speed optimization is claimed. Artifacts are in
`/mnt/external/demosaic/v102-reviewed-corpus-fullframe-20261023-v1/`.
The original controller and worker exited successfully.
[Full-frame audit, hashes and original export receipts](results/v104-reviewed-corpus-fullframe-v1.json).

## V111 final20k context comparison

![Six GFX contexts: noisy, V104, V111, RawNIND pre-upsampled and separate ISO100 reference](images/v111-early-gfx/comparison.png)

[V111's completed material and real-photo review](v111-early-quality.md) adds
the same six standing regions after its original20k endpoint. These are
**512-pixel context** restorations, native160 cells and shared+2EV, with reused
V104 and stronger RawNIND-preup outputs. V111/V104 look close: coherent mesh and
building edges persist, while fine foliage and saturated-sign structure remain
soft. All30 cells were actually viewed. The independent ISO100 f/5.6 image is
qualitative, not GT; these are not new102MP exports.
[All18 triplets, checkpoint/source/ROI/noise/display metadata](images/v111-early-gfx/manifest.json).

## Stronger released RawNIND reference

The [pre-upsampled RawNIND comparison](rawnind-variants.md) adds a stronger
released reference, improving all 12 selected photographic cases and eight
of nine development scene means over the half-resolution model. The released
width48 model has also been checked and does not improve the matched panel means.

![Six native GFX contexts: noisy, V104, RawNIND half, pre-upsampled, width48 and independent ISO100 reference](images/rawnind-three-variants-current/gfx/comparison.png)

These are matched **512-pixel context** restorations with unchanged native 160
display cells and shared +2EV; the complete 102MP comparison above retains
its original half-resolution reference. V104's exact retained CPU predictions
are reused. The alternative improves some coarse sign/rail structure over
half, but foliage remains soft and mesh less regular than V104. Shared display
clipping limits saturated-light comparisons. Width48 retains coarse fence mesh
and a conspicuous periodic grid/grain in the blue sign. The separate ISO100 f/5.6 capture
remains a qualitative reference, not GT or a pixelwise scoring target.
[All 24 triplets, source/ROI/checkpoint and display metadata](images/rawnind-three-variants-current/gfx/manifest.json).
All 36 cells in this additional board were actually viewed at native resolution.

## Other useful comparisons

The [V101/V102/V103 complete-frame gallery](images/current-gfx-v102-v103-fullframe/gfx-comparison.png)
([metadata](images/current-gfx-v102-v103-fullframe/manifest.json)) preserves the
previous comparison and its separate timings.

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

The [current V104 conditioning study](noise-conditioning.md#real-gfx-contexts)
compares .50/.75/1.00/1.25× variance on the same six cached512 contexts. Lower
strengths retain more texture and grain; the nominal1× protocol is unchanged.
A local sky check finds normalized noise scale close to1, while the exact-target
contexts show lower high-noise PSNR under the alternative strengths. These
context results supplement the full-frame comparison above.
The [Q2,Sony a7RII and GFX50R comparison](cross-camera-qualitative.md) adds six
low-ISO regions for V102/V104 without a clean reference. The
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
`.cache/current-quality-20261023-v1/reviewed-corpus-fullframe-v1/`.
Its plan binds the fixed checkpoint hashes, source code, protected local RAW
cache and six ROIs. All seven preceding evaluation stages finished before
this GPU job began. Crops are extracted after complete-frame blending and
retain exact source/reference pixels. Preserve this evidence and use a fresh
output directory for any later model comparison.
