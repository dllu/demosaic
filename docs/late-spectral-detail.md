# Late spectral innovation pilot

V147 is training a small correction after the frozen V143 output. **Quality is
not measured yet.** The ten-update CUDA smoke test and genuine eight-plus-two
optimizer resume passed. Production has a fixed 1,000-update horizon; both final
raw and EMA endpoints have a prospective review. The useful recommendations in
[current model](current-model.md) remain supported by their existing comparisons.

The [V146 window experiment](v146-window-transfer.md) found no useful gain from
larger Fourier support alone. This pilot changes the route through the model:
the actual observed-minus-parent RAW spectrum reaches camera RGB after the
frozen restoration network. It does not pass through that network again.
The [implementation](../src/demosaic/late_spectral_detail.py) is a research
component, with no ordinary inference CLI integration yet.

## Component and supervision

The 30,402 parameters occupy twelve tensors. Weighted affine removal and tapered
overlapping FFT frames analyze the original four CFA phases and the parent's
sampled camera RGB. The maximum frame is packed256/native512, with 50% overlap;
shorter contexts use the largest fitting power of two. They execute the head
rather than bypassing it.

A circular 3×3 spectral convolution uses signed cross-phase Gram coordinates,
noise-normalized power, CFA placement and frequency coordinates. A shared signed
gain multiplies the four-phase innovation. Its observed-power factor makes
per-phase constant inputs exactly inactive even when learned weights and the
parent output are nonconstant. A dilated packed-grid CNN estimates local support
from observed RAW, sampled parent, proposed correction, variance and CFA layout.
Fixed signed Malvar interpolation then adds the supported proposal to the parent.
The frequency band covers native periods about 4.4–64 pixels.

Neither learned gain is a calibrated probability. The frame-noise proxy is the
mean tapered variance, not an exact covariance after affine fitting. The constant
input property does **not** establish safety on noisy flats or near strong edges.
Targets and ISO100/JPEG references never enter the forward inputs.

Pixel and finite-difference Charbonnier errors use each image's mean input-noise
standard deviation, floored at 2 DN16. Their epsilons are .01 and .003 in those
units; the gradient term has weight .25. An auxiliary coefficient error, also
weighted .25, supervises the innovation before local support. Mesh and weak
texture batches receive four times the other source weights. This combines an
architecture, loss and source-distribution intervention; it cannot isolate the
cause of any difference from V146.

## Fixed training and review

The [recipe](../configs/quality-v143-late-spectral-v147.yaml) uses AdamW at .001,
50 warmup updates, cosine decay, clipping at1 and ramped EMA. Batch size is4.
Procedural mesh/weak/flat/mixed-edge batches are native512; photographic batches
are native256. Source probabilities are .35/.10/.15/.15/.25 respectively.
Photographs have additional faint-contrast and dark-exposure variation.
The unchanged 90,782-photo pool and 27 reviewed regions retain bin4 → geometry →
area2 construction, with zero optical PSF. Smaller photographs are not stretched
or tiled to manufacture512 support. All sixteen review photographs are
validation-only in both source manifests. The GFX scenes and their siblings
are outside these Commons-only training sources.

The discarded ten-update smoke run covers every source type, native512/B4,
ADC-only and ISO6400 flat conditions, all twelve parameter gradients and a real
checkpoint/optimizer reload at update8. Peak allocated CUDA memory was
3,178,908,672 bytes, about2.96GiB. All parent weights and the official DINOv3
ConvNeXt-Small backbone stayed exact. Production starts a fresh head and
optimizer, adopting those ten already constructed input/parent batches without
replaying their noise or parent forwards.

Both step1000 endpoints are locked for:

- The same 766 cached cases: present/absent procedural meshes, faint/dark
  photographs including organic384 contexts, native256 flats, 72 fresh native512
  flat fields, and both standing GFX scenes under their retained priors.
- Thirty-two additional freshly noised analytic scenes: four strong-edge/bar/
  stripe patterns × four CFAs × ISO6400/ISO12800. The exact constant quiet ROI is
  `[80,176,160,160]`, next to stronger structure. This is a synthetic control,
  not an independent photograph.
- Unclipped full/central160 camera-RGB errors, mesh response and blank spill,
  photo DCT16 gain **and** error, and full/central flat spatial/coarse variation.
  Real ISO100 AHD and camera JPEG references remain unscored and are not GT.
- Independent NumPy64/Decimal reductions and pixel checks, followed by actual
  viewing of native160 comparisons. The planned triplets share source, ROI,
  display transform, noise conditioning and checkpoint binding. Rendering alone
  will not be recorded as a human quality review.

The queued work adds1,532 component forwards on the main registry and64 on the
mixed controls. Main-registry parent predictions are adopted with verified
hashes; mixed controls require32 new parent/DINO calls. There are32 new noise
constructions for the mixed controls, completed during preparation. These
evaluation counts exclude training and unit tests.

The [independent input audit](results/v147-mixed-input-audit-v1.json) reconstructs
all32 mixed targets with Float64 closed-form scenes and area averaging, without
Torch or new noise draws. Maximum target discrepancy is0.02589 DN16 from FP32
trigonometry/pooling. All quiet patches are exactly constant, CFA/WB/matrix
bindings match, variance maps are bit-exact, and measurements lie on the16-bit
ADC grid. Maximum noise mean/second-moment deviations are3.10/2.66 standard
errors. These finite-sample noise checks validate the prepared controls; they
do not establish camera calibration or trained-model safety.

## Evidence and execution state

The active cache is `.cache/quality-20261103/V147-late-spectral-v2/`.
`plan-v1.json`, `quality-design-v1.json`, `review-plan-v1.json` and
`postprocess-plan-v1.json` bind frozen source, inputs and the fixed review order.
The [public evidence index](results/v147-late-spectral-preparation-v1.json)
records the preparation and smoke result. Quality results, native viewing and
integration remain pending; no gain or safe default is claimed.

The user paused the run near update 550. The worker and both controllers were
suspended with exact PID/create-time checks. On explicit resume, the original
worker continued in memory; only its two waiting controllers were replaced to
reset wall-clock deadlines. No checkpoint reload, noise redraw, new training
worker or recipe change occurred. The
[resume evidence](results/v147-resume-v1.json) preserves the original status
bytes and verifies all 83 frozen neural sources and every review-stage argument
unchanged. `postprocess-plan-v2.json` carries the replacement controller; the
original plan and source remain preserved.

An initial preparation in the separate `V147-late-spectral-v1/` cache stopped
before noise construction or training because its exclusion assertion also
rejected validation membership. The corrected check tests training membership;
both attempts remain preserved. A separate scope clarification preserves the
mixed-scene design bytes: the slanted edge's coordinate lower bound applies
within the declared quiet ROI's vertical range, not every image row. All32
quiet targets were asserted constant when prepared. No inputs or ROIs changed.

The work uses only repository/external caches and does not access `/mnt/dataz`
or decode RAWs. See the
[timestamped diary](../diary/2026-11-03-09-28-13-late-spectral-pilot.md) for this
decision and the unresolved quality question.
