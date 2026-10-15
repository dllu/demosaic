# Quality and noise diagnostics

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
