# Full V6 validation and inference precision

The user confirmed DINOv3 access. The genuine revision-pinned ViT-S/16 weights
were already downloaded and in use; no random substitute is used. The full
44732-source corpus run continues toward 100000 steps with 40170 photographic
training sources, 20% procedural draws, 10% smooth draws and 10% ADC-only noise.
At step31000 the balanced monitor is 32.07884 dB/0.92769 SSIM; this is a small
training monitor, not the full held-out result below.

The complete paired suite compares frozen V6 step20000 (SHA256
ba3e0e05a5b2e26b348c5edfc94559267b59a5e48256d0a236464f74e5d8f761)
with frozen V4 step30000. On 427 photos, V6 reaches camera/rendered PSNR
37.6539/30.9189 dB and SSIM 0.91046, versus V4 36.4313/30.3731/0.90064,
RawNIND CFA-LS 31.2171/26.6708/0.78717, and the variance-adaptive classical
prior 35.0546/29.2970/0.88810. V6 wins mean PSNR and SSIM in every declared
condition, including ADC-only (31.1811/0.93908 vs Malvar 29.9225/0.92935).
V6-V4 rendered gain is 0.5458 dB (source-bootstrap 95% CI 0.4906–0.6006).
However, the 16 independent procedural stress sources favor V4 by 0.6586 dB
and 0.01592 SSIM. This remains a real limitation, not a passed final gate.
Receipts: docs/results/prior20k-vs-main30k.json. Full local artifact:
/mnt/external/demosaic/evaluation/prior-v6-mid-vs-main30k/.

Expanded the clipping diagnostic to four HDR scenes, two white balances and
all four CFA phases, with frozen checkpoint receipts, actual BF16 inference,
channels-last tensors, and the suite's six-pixel boundary-ring metrics. V6 is
36.258 dB / boundary chroma MAE 0.01030 versus RawNIND 26.104 / 0.03598.
V4 has lower boundary chroma error (0.00890), despite lower overall PSNR.
Numerics and procedural-scene aggregates are saved in docs/results. Neutral
highlight colors visibly improve, without claiming universal absence of fringes.

Recent night crops reduce V4's grain substantially; RawNIND still suppresses
flat pavement variation more strongly. Separate Q2 rock texture, Sony a7R II
fuselage/windows, GFX50R architecture and GFX100S streetcar crops were inspected.
The Sony RawNIND crop has a conspicuous magenta spot on the white fuselage that
is absent in V6's crop. These are local qualitative observations using nominal
noise priors, without clean ground truth. Personal photos remain read-only,
local, and outside training and Git.

A matched 16-photo / seven-condition RGGB diagnostic at identical channels-last
layout and global IEEE policy gives BF16 31.8760 dB/0.924986, FP16
31.8960/0.925621, FP32 31.8961/0.925639. A four-DN sine around gray 0.5 changes
the learned correction by RMS 1.10e-8 (BF16), 8.95e-6 (FP16), 3.08e-6 (FP32).
This is a response check, not an accuracy score. Physical FP32 interpolation
already preserves fine contrast in every mode. Added scripts/compare_precision.py
with fixed observations, paired intervals, frozen weights and source snapshots.
The same result was reproduced through the committed script. New explicit
--precision options on infer/quality/benchmark leave the historical BF16 default
and active training unchanged; FP32 disables TF32 and nested autocast.

The complete FP16 channels-last suite reaches 30.9407 dB/0.911183 on all
427 photos and 29.9172/0.901137 on the 16 stress images. The matched full
channels-last BF16 comparison completed: FP16 improves photo PSNR by 0.02181 dB
(95% source-bootstrap CI 0.01967–0.02481) and SSIM by 0.000723
(0.000661–0.000783), with gains in every condition. Procedural means improve
by 0.00865 dB and 0.000333 SSIM. This small gain does not close V6's stress
deficit to V4. Both evaluations have identical source/protocol/weight hashes.
Receipts and intervals are in docs/results/prior20k-fp16-vs-bf16.json.
Quality receipts now state precision/layout and use the deployment CUDA layout.
The raw-crop and flat-response tools also support the selected precision/layout.

FP16 step20000 processed a full GFX100S streetcar RAW to 8746×11662 RGB16
linear and ICC-sRGB TIFFs, each about 612 MB. Both 16-bit tags are verified;
a 256×256 sample contains >22000 unique values and >195000 off-8-bit-grid
channel values. Finite input/output checks pass in the inference/TIFF path.
Restoration was 36.689 s, end-to-end 57.334 s, with training and quality
validation concurrent; this is not an idle benchmark. Peak CUDA allocation
0.820 GB excludes host arrays and allocator reserves. The full-frame preview
and native 512-pixel crops centered on regular tile strides show no obvious
seams; this visual sample is not an exhaustive seam proof. Private outputs:
/mnt/external/demosaic/real-raw/prior-v6-step20k-fp16-streetcar-*.tiff.
The public numerical receipt omits the private source filename.

All 52 tests pass, including CUDA FP16/BF16 preservation of four-DN contrasts
through tiled interpolation/blending and explicit FP32 nesting/exception recovery.
Ruff passes. Full convergence, broader final validation/test, final RAW quality,
and idle final-model 100 MP timing remain. No external processes were stopped.
