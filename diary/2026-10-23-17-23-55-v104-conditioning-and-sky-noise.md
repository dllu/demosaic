# V104 conditioning, real GFX detail and sky noise consistency

Recorded: 2026-10-23T17:23:55-07:00 (America/Los_Angeles).

Refreshed the fixed conditioning-strength test for the current V104 final20000
EMA. The twelve saved held-out observations use the same four source contexts
and ADC/ISO100/ISO12800 conditions, with no new data or noise draw. Four declared
variance factors1/.5/.75/1.25 multiply shot/read coefficients and the supplied
variance map, while actual noise/target arrays stay fixed. Verified all91 EMA
tensors, the official frozen Tiny state,48 real DINO-backed forwards and
unchanged weights/configuration/parameter IDs/inputs/Torch RNG. All12 original
V104 scores and native PNGs replay exactly; ADC predictions are identical under
all four strengths. Source and active training recipes are unchanged.

At ISO12800 the four-source mean PSNR is33.49300dB at1x,31.07231 at.5x,
33.08845 at.75x and33.34016 at1.25x. Every alternative loses PSNR on all four
sources. At ISO100, means are40.80494/40.79216/40.80141/40.80539 respectively;
changes are small. Lower conditioning retains some useful fine structure and
additional grain. The unchanged pre-existing Hann240/frequency1/16..1/4
descriptive projection gives mean GT-correlated gain.96509 at1x versus.98760
at.5x, with off-target RMS.004276→.004955. Single-draw correlation/sharpening
can contribute; this is evaluation, never a fitted inference correction.

Repeated all four strengths on the six standing GFX512 contexts with cached
Bayer/reference arrays only:24 actual CPU FP32 DINO forwards, no RAW decoding
or original/HDD reads. Foliage/wall/fence backgrounds show more structure and
grain at.5x,.75x is milder, higher strengths smooth further, and sign detail
stays soft. The ISO100 f/5.6 capture remains a separate qualitative reference,
not GT; no pixelwise reference scores or whole-frame claim. New CPU1x output
matches prior CUDA FP32 within1.91e-6 camera units and one RGB8 code, explicitly
recorded as numerical parity rather than byte-exact replay. All comparisons
share the new CPU implementation, original ROIs and+2EV display.

A local input-only check on the fixed sky context computes disjoint2x2
same-phase Haar-HH coefficients and divides each by the predicted noise standard
deviation. Four robust normalized sigma estimates are1.01544/1.00556/.99963/
.99193, implying variance factors1.0311/1.0111/.9993/.9839. This same-capture
check offers little indication of a factor2 variance overestimate in that sky;
it is not independent camera calibration or an identification of shot/read
components. Scene texture/correlation constrain the interpretation. No model
output or ISO100 reference enters this diagnostic.

Independent NumPy64 WB/matrix/gamma/MSE arithmetic checks all48 saved synthetic
linear/rendered PSNR values and all source means; it does not independently
reimplement SSIM. All216 private source-triplet panels reproduce the saved
floats exactly. Published48 selected native triplets: eight low-noise,16
high-noise and24 GFX. Viewed all72 distinct native board cells at original
resolution, with identical noisy/GT/reference pixels across strengths.
[Current V104 guide](../docs/noise-conditioning.md) ·
[Synthetic execution and audits](../docs/results/V104-conditioning-probe-CPU-v1.json) ·
[Real GFX execution, parity and sky check](../docs/results/V104-GFX-conditioning-CPU-v1.json).

The old V101 material/path/preview prose is preserved as an explicitly versioned
study, with a pointer to the current guide; existing receipts/pixels retain
original bytes. Updated the GFX and model guides and research summary. Corrected
the GFX guide's remaining V100/V102/V103 cross-camera description to V102/V104.
The nominal protocol and current selector remain unchanged. V111/V112 continue
to address faint-detail supervision; the separate full427 ADC photo comparison
and its exact-owner review queue remain active. At17:23 PDT, that comparison
had290/427 sources and3480 score rows, while V111 had logged step6150.

Final validation rechecked57 receipt references/28 unique hashes,
all48 public triplets/72 native cells, 176 local links/fragments across
seven Markdown files, eleven unchanged frozen plans and eight live exact
PID+creation handles. Original selector and machine receipts retain their bytes.
Independent maximum PSNR discrepancies: {'linear_psnr': 4.310213384428607e-06, 'srgb_psnr': 3.7646315362849236e-06}dB.
Private final verification: `.cache/current-quality-20261023-v1/V104-conditioning-probe-CPU-v1/final-verification.json`.
