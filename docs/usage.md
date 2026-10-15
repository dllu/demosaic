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

The larger experiment uses `configs/dino-noise-24576.yaml`, initialized from
the completed 20k DINO run. It requires the frozen audited 24576-source manifest.
`noise_modulation: true` adds identity-initialized spatial conditioning from log
sensor variance at every scale. `physical_fp32: true` keeps interpolation,
camera transforms and rendered loss in IEEE FP32 while neural features use BF16.
Old checkpoints lacking this field retain their historical arithmetic on load.
New checkpoints record it explicitly. Changing this mode requires a new run via
`--initialize`, not an exact continuation via `--resume`.

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
