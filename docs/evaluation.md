# Quality and noise diagnostics

Every improved-model performance report must include at least two small 100%
noisy/denoised/GT crop triplets. Both `demosaic quality` and
`scripts/evaluate_paired_raw.py` now write `report.md`, native PNG triplets and
JSON crop receipts automatically, independently of the optional overview gallery.
Each panel is 160×160 pixels with no resizing, using common WB, color transform
and exposure. The noisy view is Malvar demosaicing without denoising; PNGs are
8-bit sRGB previews of the unquantized evaluation arrays. Open the original PNG
at 100% if a Markdown viewer scales it. Quantitative evaluation remains floating
point and inference still supports 16-bit TIFF output.

Synthetic reports select the first two source entries, the protocol's first CFA
pattern and the condition with greatest shot+read coefficients. Real reports
select the first two scene names, highest-ISO capture in each scene, middle
prepared tile and its center. These choices precede model output inspection;
all methods use the same regions. Receipts retain source identities, coordinates,
model identity and display settings; summary JSON holds full checkpoint hashes.
Synthetic GT is exact. Paired real RGB is an auxiliary calibrated AHD reference;
primary real scores use measured clean CFA samples. Independently captured
personal photos require an explicit qualitative-reference label; see
[the GFX scene](gfx-qualitative.md). Add representative native crops to the README
when promoting an improved model, and preserve any visible failures in its report.

## Multi-condition evaluation

`demosaic quality` freezes the exact checkpoint bytes before loading them, so
ongoing training cannot change the evaluated model. It records weight hashes,
source manifest hash, model configuration, all physical observation parameters,
per-image metrics and paired source-level bootstrap intervals. Predictions from
every method use exactly the same noisy observations. Noise seeds depend on the
source ID, condition and CFA pattern, not the model or batch order.

Current runs also archive the evaluation source, manifest and protocol. Physical
color transforms, classical interpolation and metrics use IEEE FP32 even inside
autocast. The learned network may use BF16. Checkpoints predating the precision
fix retain their original interpolation/DINO-preview arithmetic; their effective
configuration is recorded so old predictions remain reproducible. Historical
scores generated before this fix retain their original protocol and source hash.

```bash
source scripts/env.sh
uv run demosaic audit-split /mnt/external/demosaic/commons-v1/commons-8192.jsonl \
  /mnt/external/demosaic/audits/commons-8192-v1
uv run demosaic quality /path/to/dino/best.pt /path/to/control/best.pt \
  --manifest /mnt/external/demosaic/audits/commons-8192-v1/manifest.jsonl \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/quality-v1
```

The default protocol in `configs/evaluation.yaml` tests all four Bayer phases
and seven declared noise/exposure conditions: ADC quantization without stochastic
noise, ISO 100/1600/12800 priors, underexposure, overexposure, and the earlier
diagnostic noise setting. ISO labels describe priors, not measured profiles.
Native 256-pixel crops from the binned cache avoid the additional shrinking used
by the original training-validation diagnostic. Metrics exclude eight sensor
pixels at each border. SSIM uses Gaussian 11×11 windows, sigma 1.5, RGB range 1,
valid windows and FP32 convolution without TF32. No intermediate 8-bit rounding
is applied. This protocol must not be compared directly to published scores with
different synthesis, clipping, bit depth or boundary conventions.

In addition to camera-linear/rendered PSNR and rendered SSIM, the suite measures
chroma error, gradient error, highlight-boundary chroma/RGB error, and shadow
PSNR. Missing regions produce null metrics with explicit valid-image counts.
The highlight boundary is a six-pixel ring around rendered reference values
at least 0.98; shadow pixels have mean reference camera RGB below 0.02. Overall
means first balance conditions within each image, then images. Bootstrap paired
differences resample images, not correlated pixels or repeated CFA observations.
Procedural stress cases use separate seeds and are reported apart from photos.

Use `--limit 8 --synthetic-count 2` for a software/early-model diagnostic, not a
quality claim. Final comparisons require complete held-out sources, matched
training budgets, real RAW inspection and additional camera/noise conditions.

The suite includes independently implemented
[Malvar–He–Cutler 2004 filters](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/Demosaicing_ICASSP04.pdf),
with WB applied before interpolation and undone afterward. This is a useful
classical demosaicing comparator, not a denoiser. RawNIND is evaluated with both
global and per-channel least-squares gains against observed CFA samples; neither
method uses clean targets. Its original network and weights remain separately
fetched and checksum-pinned.

New runs also include `Wiener7+Malvar2004:WB`, an independent variance-adaptive
classical comparator. It is not the learned V6 model: V6 predicts additional
corrections using the restoration network and DINO features. Historical suites
predating this comparator retain their original source snapshots and method lists.

New quality runs use channels-last CUDA weights and inputs, matching the tiled
inference layout, and record neural precision/layout in each model receipt.
Historical evaluation used contiguous tensors; its archived scores remain
unchanged. `--precision float16` or `--precision float32` selects another compute
mode. Compare precision modes with the same layout and observations before
attributing a difference to numerical precision alone.

For a matched three-precision diagnostic, `scripts/compare_precision.py` freezes
one checkpoint and uses the same RGGB observations, channels-last layout and
global IEEE FP32 policy in every mode. It reports paired source-bootstrap
intervals and a separate ADC-only fine-contrast response check. The latter
measures changes in neural correction relative to a flat input, not accuracy.

```bash
uv run python scripts/compare_precision.py /path/to/model.pt \
  --manifest /path/to/audited/manifest.jsonl --images 16 \
  --output /mnt/external/demosaic/evaluation/compute-precision
```

`scripts/diagnose_highlights.py` provides a separate controlled clipping check:
four HDR scenes (neutral circle, slanted edge, colored emission and detailed
sign), two white balances and all four Bayer phases. It applies physical sensor
clipping and the same 16-bit ADC/noise generator as the suite. It freezes
checkpoints, runs the requested inference precision/layout, and records the
same boundary-ring metrics, individual cases and a visual comparison. Its
32 cases per model complement the photographic suite.

```bash
uv run --extra eval python scripts/diagnose_highlights.py /path/to/model.pt \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/highlight-boundaries
```

The 24k-source training config monitors 16 native validation crops across all
28 CFA/condition cases, and selects EMA checkpoints by balanced rendered PSNR.
It still logs the older single-condition diagnostic. The panel is a training
monitor, not a substitute for full held-out evaluation. Its archived protocol hash
must match on resume; noise generation uses private generators and leaves the
training RNG unchanged.

`scripts/probe_noise_response.py` measures a complementary failure mode on
constant scene-linear fields at four intensity levels. It records absolute
camera bias, residual standard deviation, its ratio to bilinear, and unclamped
camera PSNR. The default is a 256-pixel field with a 32-pixel excluded border.
These scores measure noise suppression and bias only; a method that destroys
detail can score well, so they cannot replace photographic quality checks.

`scripts/compare_tiling.py` exercises the actual host-streamed tile driver,
comparing 256/64 and 512/64 sensor-pixel tile/overlap geometry. It selects every
validation image large enough for a native 512-pixel crop, without enlarging
references, and adds three 1024-pixel procedural scenes (flat, chirp and clipped
disc). Those scenes also receive a single-1024-tile prediction. All methods share
observations; single-tile predictions are a sensitivity reference, not ground
truth. Shared eight-pixel strips centered on 256/64 overlap regions measure
local RGB error alongside errors away from those strips. Scene texture affects
both, so these measurements complement visual seam checks.

```bash
uv run python scripts/compare_tiling.py /path/to/model.pt \
  --manifest /path/to/audited/manifest.jsonl --precision float16 \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/tiling
```

```bash
uv run python scripts/probe_noise_response.py /path/to/model.pt \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/flat-response
```

## Duplicate screening

`audit-split` checks all protected sources against the corpus using 256-bit
directional fingerprints in eight rotations/reflections, aspect ratio, and
normalized thumbnail correlation. It leaves training membership unchanged.
Training-linked protected images are excluded, and test images linked to already
used validation scenes are excluded. It also removes within-split duplicate
weighting and marks protected images with insufficient fingerprint contrast.

The 8192-source audit found no matches at Hamming distance <=8 and correlation
>=0.99, leaving 7378/427/387 sources. This is evidence for this screen, not proof
of complete scene separation: crops and different viewpoints can still evade it.
Original caches and source manifests are never modified. Review `audit.json` and
its excluded IDs before interpreting evaluation counts.

The frozen 24576-source manifest audit excluded one training-linked validation
image, leaving 22059 train / 1262 validation / 1254 test sources. Test images
remain unused for model selection. Broader preparation continues separately;
training uses the immutable audited manifest.

## Paired real-RAW evaluation sources

The publisher's [RawNIND dataset](https://doi.org/10.14428/DVN/DEQCIM) provides
real noisy/clean RAW pairs. Its [Dataverse metadata](https://dataverse.uclouvain.be/api/datasets/:persistentId/?persistentId=doi:10.14428/DVN/DEQCIM)
identifies release 1.0 as CC BY-SA 4.0; `permissions.txt` also records individual
scene credits and CC0 grants. The downloader preserves those records and the
complete source catalog. Files stay outside Git and outside Commons training.

```bash
uv run python scripts/fetch_paired_raw.py --split both \
  --output /mnt/external/demosaic/references/rawnind-dataset
```

The development subset uses four explicitly named scenes outside the publisher's
test reserve. The pretrained RawNIND comparator may have trained on these scenes,
so development comparisons are not an unbiased test of that comparator.
The separate test subset uses all 16 publisher-reserved Bayer scenes, including
six marked as an unknown sensor. Keep them unused for model selection.
Both subsets select up to two clean frames and two noisy frames per scene using
only filename ISO metadata: nearest to ISO1600, plus the highest remaining ISO
at most 12800. Publisher XMP sidecars are excluded from image selection.

Every RAW must match its published byte count, MD5 and descriptor SHA1. A local
SHA256 receipt is also retained. Existing invalid files are preserved and
rejected; interrupted downloads leave no completed manifest. The checked release
produces 13 development files (366 MB) and 57 test files (2.090 GB). See
[the acquisition receipt](results/paired-raw-acquisition.json).

Acquisition alone establishes no quality result. Pair alignment, exposure gain,
reference processing and noise conditioning must be explicit before scoring.
On the checked Sony reference, LibRaw AHD with raw color, unit WB, linear output
and auto brightness disabled still differs by about 6.9% from this project's
per-channel-white-level sensor units. Calibrate RGB references against their own
clean CFA measurements; do not compare these units directly. Raw-domain scores
against measured reference samples can avoid a demosaicer-dependent ground truth.

`prepare_paired_raw.py` now performs bounded green-plane integer registration,
fits one exposure gain per clean/noisy capture, calibrates auxiliary AHD RGB
against that clean capture's own CFA, and saves a fixed 3×3 grid of 512-pixel
crops. The primary reference consists of measured clean CFA samples, with the
reference color phase adjusted for odd registration shifts. Saturated and
out-of-rendering-gamut reference regions are excluded from that primary score.
Noise conditioning uses only the noisy input's reliable Haar fit, with a
disclosed nominal ISO fallback. Source RAWs are never modified.

```bash
uv run python scripts/prepare_paired_raw.py \
  /mnt/external/demosaic/references/rawnind-dataset/manifest-development.json \
  --output /mnt/external/demosaic/evaluation/paired-prepared
uv run python scripts/evaluate_paired_raw.py /path/to/model.pt \
  --prepared /mnt/external/demosaic/evaluation/paired-prepared/manifest.json \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/paired-comparison --gallery
```

The evaluator hashes prepared crops, freezes checkpoint bytes, archives source,
and reports measured-sensor PSNR plus auxiliary AHD-derived rendered metrics.
It averages crops within capture, captures within scene, then scenes; bootstrap
intervals resample scenes. Low-ISO captures retain noise and AHD is an auxiliary
reference, so neither metric is exact ground truth. The small development sets
do not support a broad generalization claim.

RawNIND's publisher preprocessing retains signed and above-white measurements
and uses the global ADC white level. The adapter now follows that convention,
including per-phase conversion from our camera-white normalization. Earlier
reports clipped its input and understated this comparator; those archived
reports are historical and require a new comparison. New synthetic suites also
run RawNIND in IEEE FP32. See the real development results in
[experiments](experiments.md#paired-real-raw-development-and-camera-conditioning).

## Noise profiles

`noise-profile` estimates the coefficients of `Var(y|x)=shot*x+read` on normalized
camera RAWs without modifying the original. It samples each CFA phase separately,
uses three orthonormal Haar bands, rejects clipped/textured patches with a
detrended low-pass check, and fits nonnegative coefficients to intensity-binned
variance medians. Bootstrap intervals and failure reasons expose unstable fits.

```bash
uv run demosaic noise-profile photo.raf /mnt/external/demosaic/profiles/photo.json
uv run demosaic infer /path/to/best.pt photo.raf /mnt/external/demosaic/photo.tiff \
  --noise-profile /mnt/external/demosaic/profiles/photo.json
```

A profile with inadequate flat patches or intensity span cannot identify both
coefficients and is rejected by inference. Profiles must match camera and ISO.
You can still provide explicit `--shot` and `--read`. A good regression fit does
not establish physical calibration: residual texture, correlated noise and
clipping can bias a single-image estimate. Dedicated flat/dark captures are
stronger evidence. Shot/read priors alone do not establish final quality.

Relevant primary research: [Foi et al., 2008](https://pubmed.ncbi.nlm.nih.gov/18784024/)
on single-image Poisson-Gaussian fitting, and a [2021 noise-parameter estimation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8705815/)
on weak-texture selection. This implementation is a separately written
conservative diagnostic, not a reproduction of either paper's results.

Initial real RAW estimates: GFX50R ISO100 shot≈2.01e-5 (nominal 2e-5), Sony a7R II
ISO400 shot≈8.20e-5 (nominal 8e-5), Leica Q2 ISO100 shot≈4.37e-5 (nominal 2e-5).
The Q2 result motivates measured conditioning rather than assuming all cameras
share one full-well prior. These observations are scene-dependent estimates.
