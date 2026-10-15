# Data, training and inference

## Environment and storage

Run commands from the repository root after `source scripts/env.sh`. This keeps
uv, Hugging Face, Torch, compiler caches and temporary files inside the repository.
Large generated data and runs belong in `/mnt/external/demosaic`. Source photo
directories and the existing Commons corpus are read-only; output APIs reject
writes outside this repository and `/mnt/external`, and reject the Commons source.
Do not run environment/setup commands without the cache environment.

## Commons preparation

`demosaic prepare --output /mnt/external/demosaic/commons-v1 --limit 1024`
queries the existing SQLite index in immutable read-only mode. It accepts CC BY,
CC BY-SA, CC0 and public-domain records, records the original author, license,
credit and URLs, and omits unknown or noncommercial/no-derivatives licenses.
It does not redownload or modify originals. Original ICC profiles are converted
to sRGB before inverse transfer and averaging. Original rendered photographs are
not true sensor ground truth; aggressive binning reduces, but cannot eliminate,
their prior ISP artifacts. Standard JPEG inputs are decoded at their native 8-bit
precision, then all averaging is performed in float32 linear light and cached as
uint16, gaining quantization levels without claiming recovered sensor bit depth.

Only images at least 2048 pixels on each side enter the default 8× binning and
256-pixel-crop recipe. Each output averages 64 source samples. No crop crosses
source splits: SHA-based source IDs deterministically assign 90/5/5 percent to
train/validation/test and deduplicate exact source hashes. Near-duplicate photos
of the same scene may remain: this is **source-disjoint**, not a verified
scene-disjoint benchmark. Additional scene deduplication is required before a
strong generalization claim. `manifest.jsonl`, `summary.json`, and
`errors.jsonl` document the result. Image files and the manifest are atomically
renamed, and rerunning reuses completed caches. Use a new destination when changing
the binning recipe. Each worker decodes only one original at a time (120 MP cap)
and processes float averages in small bands. `--workers 4` enables bounded
parallel preparation; an OS lock protects each destination. Recipe mismatches
fail explicitly, and prepared caches carry SHA-256 checksums.

The completed local preparation contains 44732 licensed sources (40170 train,
2306 validation, 2256 test); 875 records were filtered by the license policy and
14 failed decoding/preparation. `commons-44732.jsonl` is an immutable copy of the
completed manifest. The full screen excludes four protected sources, leaving
40170 train / 2303 validation / 2255 test / 4 excluded. The audited manifest is
`/mnt/external/demosaic/audits/commons-44732-v1/manifest.jsonl`; training still uses
the previously frozen, audited 24576-source manifest.

For an additional camera-linear target source prepared directly from licensed
low-ISO Bayer captures, see [native RAW targets](native-raw-targets.md).

## Training

`demosaic train configs/base.yaml` starts the no-foundation baseline.
`configs/dino.yaml` explicitly enables a frozen pretrained DINOv3-S/16 branch;
access errors are not replaced with random weights. Both use the same restoration
architecture. The foundation backbone is excluded from EMA/optimizer copies and
restoration checkpoints; it is loaded independently from its named HF source.
Run environments must retain the matching backbone and its license.

Clean targets include 20% procedurally supersampled shapes, thin lines and chirps.
Photographic crops are shrunk or gently warped; rotations/flips precede mosaicing
so the CFA stays correct. Small Gaussian, radial, motion, coma and astigmatism
blurs diversify the optical response. Random exposure includes shadows and sensor
clipping. Camera-space targets use mild invertible color mixing and randomized WB;
this is approximate unprocessing, not a recovery of the original camera pipeline.

For normalized signal x, noise variance is `shot*x + read`. Synthetic photons are
sampled with a true Poisson distribution in electrons, then independent Gaussian
read noise is added and the 16-bit ADC clips/quantizes. Full-well priors scale with
photosite area (3–6 µm), with ISO gains from 0.5 to 128 and read noise 0.7–5 e-.
These are broad representative priors; no particular camera has been calibrated.
With `preserve_negative_read_noise: true`, a randomized ADC black offset allows
negative black-subtracted read noise, matching the native RAW convention. Older
bootstrap/v2 runs used ADC black=0, a known domain gap for deep shadows.

The model receives four spatial Bayer phases, their standard deviations and 12
one-hot phase/color indicators. It predicts linear camera RGB plus an auxiliary
clean mosaic. Camera-conditioned variants additionally receive 3 WB and 9 matrix
entries. Highlight references clip exposed linear sRGB before camera transport,
while input sensor channels still clip independently after noise. This avoids
training on the false-color white reference found in the bootstrap recipe.
It cannot recover information destroyed by complete saturation.
Losses combine linear and sRGB reconstruction, rendered gradients,
highlight-region chroma error and clean-mosaic reconstruction. Rendered training
loss does not make the inference output an sRGB image.

Training writes JSONL metrics, resolved config, `last.pt` and validation-selected
`best.pt`, with optimizer, EMA and RNG states. Resume with
`demosaic train configs/base.yaml --resume /path/to/last.pt`. The optional
`--stop-after N` makes controlled, resumable experiments. Clean draws/augmentation
are determined by sample index, independent of DataLoader worker scheduling.
CPU tests verify restart equivalence. CUDA BF16 kernels may have nondeterminism.
`--initialize CHECKPOINT` warm-starts restoration weights with a fresh optimizer,
including zero-weight expansion for new camera-metadata channels. New runs retain
a source snapshot, lockfile, and manifest fingerprint in addition to checkpoints.
Workers/batch size are bounded; a low available-system-memory threshold triggers
a checkpoint and stop. Other users' processes are never changed.
Starting afresh in a directory that already contains checkpoints is rejected;
use a new run directory or resume the existing run explicitly.

`broad_camera: true` widens training illuminants (red/blue WB 0.65–3.6) and
neutral-preserving primary mixing, including near-identity draws. It avoids
nearly singular transforms and copies no validation-camera profiles. The
default remains the historical mild augmentation so old runs keep their draw
sequence. This is a synthetic augmentation distribution, not a camera calibration.
`configs/dino-broad-camera-44732.yaml` tests it from the frozen V6 step51000 EMA.

`normalized_sensor_weight: 0.02` optionally adds observed-CFA reconstruction
error divided by clean-target shot/read standard deviation (floor 1e-4).
It strengthens deep-shadow gradients while retaining all original losses.
Rendered highlights and ADC-only draws are excluded from this additional term.
Its default is zero. `configs/dino-normalized-camera-44732.yaml` is matched to
the broad-camera experiment except for this weight; neither recipe is promoted
without real development and detail-preservation evidence.

`model.standardized_noise: true` optionally appends four local Bayer-phase
residual maps divided by sensor standard deviation. They are computed in IEEE
FP32, bounded to ±8, and zero on ADC-only inputs. The 31-pixel phase window is
reduced for small patches. Warm-start expansion gives the new stem channels zero
weights and preserves existing metadata/noise channel roles. V9/V10 compare this
option with the same initialization and original loss; it remains experimental.

For separate real RAW training, first acquire and prepare the fixed train split:

```bash
uv run python scripts/fetch_paired_raw.py --split train \
  --output /mnt/external/demosaic/references/rawnind-train32
uv run python scripts/prepare_paired_raw.py \
  /mnt/external/demosaic/references/rawnind-train32/manifest-train.json \
  --output /mnt/external/demosaic/evaluation/paired-train32-prepared-v1
uv run demosaic train configs/dino-paired-commons-44732.yaml \
  --initialize /path/to/frozen-broad-camera-checkpoint.pt
```

`paired_manifest` must point to a prepared **train** manifest;
`paired_fraction` sets the fraction of whole batches from that dataset. The
loader verifies cache checksums and refuses development/test or unknown-sensor
scenes. Training draws scenes and captures uniformly, preserves
Bayer/mask geometry through rotations/reflections, and retains signed input noise.
The step schedule is deterministic across restarts. Checkpoints hash/archive both
training manifests; a changed paired manifest or batch fraction is rejected on
resume. Measured clean CFA values supervise real detail; 4×4 AHD-derived RGB means
supply coarse color only. Low-ISO reference noise remains a limitation.

The optional `scripts/audit_paired_training.py` screens those RAW references
against protected Commons photos, recording hashes, thresholds and limitations.
Selection and near-duplicate screening do not establish model quality.

The larger experiment uses `configs/dino-noise-24576.yaml`, initialized from
the completed 20k DINO run. It requires the frozen audited 24576-source manifest.
`noise_modulation: true` adds identity-initialized spatial conditioning from log
sensor variance at every scale. `physical_fp32: true` keeps interpolation,
camera transforms and rendered loss in IEEE FP32 while neural features use BF16.
Old checkpoints lacking this field retain their historical arithmetic on load.
New checkpoints record it explicitly. Changing this mode requires a new run via
`--initialize`, not an exact continuation via `--resume`.

Training `precision: float32` selects IEEE FP32 neural forward, loss and backward,
including validation; TF32 is disabled inside those operations. The historical
default is `bfloat16`. A precision change requires a new initialized run.
`physical_fp32` remains a separate setting for sensor/color operations. FP32
training does not change inference defaults: select `--precision float32` when
evaluating that arithmetic. The flat-only V12/V13 configs are learnability
diagnostics, not recommended photographic training recipes.

`model.noise_refinement: true` adds an identity-initialized RGB correction branch
in estimated-noise units. The branch keeps IEEE FP32 arithmetic even when the
base network uses BF16/FP16. With `refiner_only: true`, only that branch trains;
all original restoration/DINO parameters are frozen. Changing that trainable
selection on resume is rejected. The photo-trained V15 recipe is
`configs/dino-paired-refiner-v15.yaml`; its frozen step5000 evaluation improves
real RAW development quality, but it is still behind RawNIND. Flat-only V14 is
rejected. See [the review and native crop comparisons](photo-refinement-review.md).

The larger `configs/dino-paired-refiner-wide-v16.yaml` has completed its 5000-step
review and supplies the current README examples. It remains behind RawNIND on
real development data. The optional `model.coarse_refinement_factor` adds a
pooled RGB correction (factor 2/4/8/16; default 0 disables it).
`coarse_refiner_only: true` freezes everything except that new branch and cannot
be combined with `refiner_only`. Its first V17 trial is not promoted. See
[residual scales and limitations](residual-scales.md).

For controlled training comparisons, `trace_observations: true` logs a SHA-256
of actual batch inputs/targets/metadata at logged steps. It canonicalizes tensor
strides and includes types/shapes; it does not hash model predictions. The option
defaults off. V18/V19 use it to verify sampled observations match while changing
only the trainable parameter selection. Hashing requires a small CPU copy and is
diagnostic overhead, not an inference feature.

`flat_fraction` optionally adds continuous-precision smooth scenes, spanning
neutral/color flat fields and gentle ramps down to deep shadows. The default is
zero, preserving existing sample draws. With `flat_fraction: 0.1` and the default
20% detailed procedural draws, 70% of training samples remain photographic.
Validation never substitutes procedural examples for held-out photographs.
The V5 config tests this targeted curriculum as fine-tuning from a frozen V4
checkpoint; it is a separate run with a fresh optimizer.

The full-corpus V6 config, `configs/dino-prior-44732.yaml`, selects
`model.baseline: wiener-malvar` and `prior_window: 7`. It uses the declared
variance map for a local phase-wise filter before Malvar demosaicing, then the
network predicts RGB and clean-mosaic corrections. The default baseline remains
bilinear for existing checkpoints. `reset_output_heads: true` resets only those
two heads during `--initialize`, so initial predictions equal the new baseline;
it does not reset them on resume. `noise_free_fraction` adds explicit ADC-only
training samples. Its default is zero and preserves the earlier RNG sequence.

`validation_protocol`, `validation_images` and `configs/evaluation.yaml` enable
the balanced multi-condition training monitor. `best.pt` then follows panel
rendered PSNR, with per-case SSIM/PSNR also logged. Its protocol is copied into
the source snapshot and checked on resume. Final full-set evaluation remains
necessary; keep the test split out of training and selection.

## Evaluation and quality

The initial `evaluate` command uses fixed crops, RGGB, fixed WB and Poisson/read
coefficients, and a fixed noise seed. It reports per-image-averaged linear and
rendered PSNR for the model and the same noisy bilinear baseline. It is a first
learning diagnostic, not the full quality gate. Do not tune on the test split.
Final evaluation must include all CFA phases, multiple noise/exposure conditions,
edge/highlight/shadow and texture crops, scene deduplication, real RAW inspection,
and correctly calibrated comparisons with RawNIND and strong current baselines.
Neither passing numerical tests nor beating bilinear establishes state of the art.

To fetch and compare the original RawNIND weights, separately licensed and
checksum-pinned:

```bash
uv run python scripts/fetch_rawnind.py
uv run demosaic evaluate /path/to/best.pt --manifest /path/to/manifest.jsonl \
  --rawnind /mnt/external/demosaic/references/rawnind \
  --output /mnt/external/demosaic/evaluation/comparison.json
uv run --extra eval python scripts/diagnose_highlights.py /path/to/best.pt \
  --output /mnt/external/demosaic/evaluation/highlights
```

The reference adapter retains native pixel geometry for all four Bayer phases
and runs the upstream network in FP32. `evaluate` reports input-mean/global
observed-CFA gain matching; `quality` reports global/per-channel CFA gains.
These methods use observed samples without target access.

## RAW and TIFF conventions

`infer` accepts Bayer camera RAWs supported by LibRaw/rawpy, or single-channel
`.npy`/`.tiff` mosaics. For generic mosaics, specify `--pattern`, `--black` and
`--white` (default 0/65535). Camera RAWs use visible sensor CFA, per-phase black
and white levels, embedded WB, and orientation. X-Trans, quad/nona Bayer,
monochrome and other arrays are rejected. The named GFX100S/GFX50R, Q2 and a7R II
are Bayer models, but actual file support must be exercised on local samples.

Supply normalized `--shot` and `--read` variance coefficients; ISO alone does not
determine noise. `Sensor.coefficients()` converts an assumed electron full well,
read noise and ISO to this convention. Measure camera-specific coefficients for
reliable results, especially at high ISO. `noise-profile` provides conservative
single-image estimates and `--noise-profile` applies reliable camera/ISO-matched
fits; see [limitations and commands](evaluation.md#noise-profiles).

The main TIFF is linear **camera RGB**, before WB and color conversion, with a
JSON description. It is not a rendered sRGB TIFF. `--preview` produces a separate
16-bit sRGB TIFF with an embedded ICC profile. Its camera-matrix conversion is a
basic preview, not an ICC/DCP-quality camera profile or highlight reconstruction.
All outputs round to uint16 once; no intermediate 8-bit output is used. Input
files are never overwritten by the inference command.

Inference streams even-aligned tiles, preserving CFA phase and using float32
weighted overlap accumulation. The default tile is 256 sensor pixels with 64
pixels of overlap. Memory stays bounded by tile features plus CPU raw/output
arrays, rather than full-image neural activations. CPU/CUDA allocations still
occupy separate memory in PyTorch on the GB10 despite shared physical DRAM.

`infer`, `benchmark` and `quality` accept `--precision bfloat16` (the historical
default), `--precision float16`, or `--precision float32`. This selects neural
compute precision. New checkpoints keep physical interpolation, the variance
prior, color conversion and overlap accumulation in FP32. Explicit `float32`
also disables TF32; CPU inference uses FP32. Training defaults to BF16.
The output sidecar records the effective compute precision and memory layout.
FP16 gives a small measured quality gain for V6: a matched 427-photo comparison
finds +0.0218 dB and +0.000723 SSIM over BF16. The 16-photo FP32 reference is
close to FP16. Use the explicit flag when reproducing those results; final-model
checks remain pending. Neither half-precision option makes the learned feature
stream equivalent to full FP32 computation.

```bash
uv run demosaic benchmark /mnt/external/demosaic/runs/base-v3/best.pt \
  --height 10000 --width 10000 --tile 512 --batch-size 8 \
  --output /mnt/external/demosaic/benchmarks/base-v3-100mp.json
```

Benchmark results include a real full-image invocation, warmup, output-finiteness
check, tile geometry, GPU name and peak allocated CUDA memory. Timings currently
cover input validation, tiled model execution/transfers/accumulation, excluding RAW decode/TIFF
encoding and setup; end-to-end latency must be measured separately for a strict
10-second photo-processing claim. `infer` additionally records complete local
decode/load/restoration/encode time as `end_to_end_seconds`. Global/coarse attention and DINO context can
vary by tile, so overlap seams require visual and numerical checks after training.
