# Measured phase evidence for the matching branch

**V178 is an implemented, untrained model variant.** It adds a zero-initialized
3,120-parameter adapter that exposes separately measured RAW frequency evidence
to the existing local-noise matching network. The adapter has real gradient
flow in CPU test fixtures. All 188 existing V172 raw/EMA tensors load exactly.
CUDA parity, actual matching gradients/memory, training and image quality remain
pending; current restoration recommendations and native comparisons are unchanged.

[Model implementation](../src/demosaic/late_phase_evidence_matching.py) ·
[CPU tests](../tests/test_late_phase_evidence_matching.py) ·
[Native preparation and preserved prototype failure](results/v178-phase-evidence-preparation-v1.json).

## Path into the model

The [V177 diagnostic](phase-frequency-evidence.md) finds useful repeated evidence
when one green CFA phase selects a frequency and the other measures it. Its
strict descriptive cutoff also misses many weak patterns and is not adopted.
The earlier frozen spectral component already sees phase spectra, while the
V172 matching branch receives local RAW innovations and its frozen restoration.
The new variant gives that matching branch direct access to measured waves and
continuous evidence from both green phases.

For each phase direction, select four principal-band frequencies using only
the selecting phase's RAW and variance proxy. The measured phase cannot change
those frequencies or ranks. Hann-tapered weighted affine removal and Fourier
variance propagation include the fitted plane. Native radial support remains
1/16..1/3 cycles/pixel, with the same conjugate/3×3 neighborhood suppression as
V177. Full input contexts have 8–512 packed pixels per axis; larger inputs need
tiling before this experimental function.

Each selected frequency supplies ten packed-grid feature channels:

| Channels | Meaning |
|---|---|
|4|Real/imaginary transported coefficients for both phases, in asinh Fourier-noise units|
|2|Continuous `log1p` power for each phase|
|2|Bounded signed real/imaginary cross evidence; negative signs are retained|
|2|Native frequency x/y times continuous total-power strength|

Two directions × four frequencies × ten channels give **80 input-only evidence
maps**. A bias-free 80→39 pointwise projection adds them to V172's existing
39 matching coordinates. Its weights start at zero. The existing matching
network then predicts its 12 packed RGB coordinates, using the unchanged local
noise output units. The frozen V169 component stays frozen/eval. No direct
sinusoid-to-RGB output or hard detection/support cutoff is added.

The new model has **2,092,026 trainable parameters** with the matching network
enabled, including the new 3,120; the frozen component has 124,909 parameters.
The initial adapter contribution is zero by construction. CPU fixtures verify
bit-exact output equality at initialization, and real checkpoint checks verify
all original tensors. This is not a claim of actual CUDA output parity yet.
The new optimizer state must be initialized or explicitly extended; loading
the old weights does not establish optimizer compatibility.

## Detail and flat-region limits

The global wave maps are features, not reconstructed wires. Their coefficients
can remain nonzero outside the true textured support, so spatial localization
must be learned and checked on actual present/absent, mixed quiet/edge and
protected real-photo comparisons. Selection reuses noisy data and its variance
proxy; cross evidence is not calibrated confidence. Both phase directions also
reuse the same observations. Native aliases remain unresolved by these green
samples alone; no sign is automatically interpreted as absence of detail.

A one-DN16-squared Fourier-variance floor provides finite arithmetic for
ADC-only coefficients. It is not a statistical threshold. Exactly constant
per-phase RAW gives zero evidence maps, including after varying the adapter
weights. This does not protect a noisy sky, whose measured coefficients are
nonzero. Zero supplied variance bypasses the new branch entirely; mixed
zero-variance cells retain the frozen output exactly in the CPU fixture even
after the adapter changes. The inherited network can still have noisy-field
error, and a learned adapter can introduce new error.

## CPU preparation completed

All **68 focused CPU checks** pass: 23 new variant checks plus the existing local
feature and NumPy phase-spectrum/split checks. They cover all four Bayer layouts,
FP32/FP64 NumPy feature agreement, rectangular/mixed-layout inputs, empty peak
slots, constant/ADC behavior, strict weight loading, frozen mode, RNG preservation,
zero initialization, mixed zero/noisy cells and gradients into the new adapter
and matching fixture. No target/reference or paired metadata enters forward.

The first prototype exposed FP32 phase-angle error in four feature comparisons:
19 other checks passed. The failed source and log are retained. Integer FFT-bin
phase is now reduced modulo its spatial period before conversion to radians;
the original tolerances were kept. This removes avoidable large-angle drift
without relaxing the checks.

The fixed native CPU profile reads only cached RAW/variance/CFA for six cases:

| Case | RAW packed shape | Evidence shape | One FP32 feature call, seconds |
|---|---|---|---:|
|Training mesh, step1|4×4×256×256|4×80×256×256|0.282|
|Training photo, step2|4×4×128×128|4×80×128×128|0.057|
|Training mixed, step4|4×4×256×256|4×80×256×256|0.225|
|Training flat, step8|4×4×256×256|4×80×256×256|0.234|
|Protected main overcast sky|1×4×256×256|1×80×256×256|0.059|
|Protected nominal cab mesh|1×4×384×384|1×80×384×384|0.099|

These are single CPU feature observations on two cores, not end-to-end model
throughput or CUDA measurements. No crop pixels are resized. All 18 images are
computed in FP32 and FP64, with independent NumPy references: **85,196,800
feature values** compared in FP64, largest absolute difference 2.25e−12. FP32/FP64
selected bins match in all six cases; FP32 feature RMS differences range
1.02e−7..1.75e−7, with largest absolute difference 2.43e−6. The largest
FP32 feature tensor during profiling is 80 MiB; peak process RSS is 1.30 GiB including
references, checkpoint and model objects. No feature tensors are archived, only
hashes, selection/power records and numerical comparisons.

One existing V172 checkpoint is loaded on CPU. Both its raw and EMA states
strictly initialize the variant with all 188 original tensors unchanged and one
new zero tensor. The profile makes zero actual matching, frozen-component,
V143/DINO or sampler forwards, zero updates/noise/source draws and no RAW decode;
CUDA is not initialized. Test-double forwards are separate from this profile.

The protected sky and cab inputs are used only for feature geometry/finite
arithmetic here, without reading their references or parent outputs, training,
model-quality scores or visual restoration claims. Both scenes and siblings
remain outside training. Originals and `/mnt/dataz` are not accessed. The
standing ISO100 captures remain qualitative references, not GT.

V175 continues in its original process with all 96 prior neural source files
and 18 completion helpers unchanged. The new 97th neural file is a separate
variant; it does not enter V175's frozen source tree. After GPU admission and
training, this variant will need the full fixed comparison and native fence,
foliage, building and sky views, including at least two unresized noisy/restored/GT
crop triplets. Until then, use the [V172](local-noise-matching.md) and
[V174](spread-sample-matching.md) reports for actual model quality.
