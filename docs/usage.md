# Data, training and inference

## Current quality model

Use **V120 Small final20k** for general restoration and continued quality training:
`/mnt/external/demosaic/models/v120-final20000.pt`. It uses DRUNet RGB
restoration and frozen official DINOv3 ConvNeXt-Small features. The
[current model guide](current-model.md) records its hash and alternatives;
[completed primary panels, diagnostics and native crops](v120-v121-primary.md)
cover full427 photos,known/unseen measured-camera and complete 102MP GFX output.
Continue quality work with the [reviewed corpus and zero-blur recipe](quality-first-training.md).
Earlier measurements below retain their checkpoint labels.
For explicit shot=read=0 inputs, the separately tested
[V114 observed-site ADC export](adc-consistency.md#current-export-and-verification) gains
.23563 dB across 427 sources/four CFAs with unchanged learned weights. All 1,708
cases improve; positive-noise profiles bypass the correction. Its report includes
actual serialized-export triplets and the increased flat-field spatial variation.
V114 Tiny retains a slightly lower tested ADC maximum; V115 Small has a slightly
higher known-camera mean and V117 a higher photo mean. The model guide records
these useful alternatives. The [V122/V123 frequency experiment](v122-v123-quality.md)
is complete and retains its fixed V115 parent. Newer experimental full-model
choices are [V131 and its ADC-only repair](current-model.md#full-model-choices).

Add `--phase-harmonic` to `infer` for the experimental local periodic-detail
correction. It runs after neural restoration and before linear/sRGB RGB16 export,
using the same observed RAW and noise conditioning. Fixed256-pixel windows
overlap at native stride128 by default; `--phase-harmonic-stride` accepts even
values 2–192. Supported-amplitude fitting (`detail`) is the default;
`edge` retains the earlier TV envelope;
`--phase-harmonic-envelope complex` selects the earlier Gaussian phase envelope,
and `scalar` reproduces amplitude-only correction. The TV solver follows the
neural device; `--phase-harmonic-device cpu` selects the CPU reference solvers.
It adds substantial runtime and does not eliminate partial-texture spill or
unverified highlight changes.
[Complete102MP results, native comparisons, wider sky and exact-flat checks](edge-phase-envelope.md).
Add `--phase-harmonic-refine-frequency` with the `edge` envelope to fit active
waves between FFT bins. [Matched full-frame/fresh validation](offgrid-phase.md)
shows clearer mesh and slightly lower texture error, with increased blank spill.
With explicit `edge`, omitting that flag preserves its original fixed-bin policy.
Select `--phase-harmonic-envelope sparse` for [connected support and refitting](sparse-phase-support.md),
which automatically includes guarded frequency refinement. It gives stronger
average response and lower mean blank spill, with worse tail cases; it remains
explicit. Sidecars record the support/refit parameters and both solvers' caps.
Select `--phase-harmonic-envelope wide` for [larger measured RAW contexts](wide-phase-context.md)
and a second frequency band, with an additive correction-variance floor. On fresh
dark recipes it raises response 14.4% over sparse support, lowers image RMS 1.2%
and raises mean added blank RMS 17.3%, with a 17.4% lower worst case. All 256 absent
neural cases and 5,120 ideal-flat matched/mismatched executions stay unchanged.
The floor can suppress useful texture; it is not calibrated uncertainty. Actual
512-pixel contexts feed the same 256-pixel local fit; smaller images retain sparse
behavior. Observed-clipped windows retain the earlier grid-TV correction.
`--phase-harmonic --phase-harmonic-envelope detail` uses reciprocal support
with the global gate applied only as selection. It improves periodic response
with higher boundary spill than `cross`; small images and observed-clipped
windows retain their documented fallbacks. [Measured quality, native crops and limits](supported-wave-amplitude.md).

Select `--phase-harmonic-envelope cross` for [reciprocal green support](cross-phase-support.md)
on the wider-context waves. It removes unsupported regions with a binary mask;
measured fresh blank spill drops 89% on average and 92% in the worst case, with
9.5% lower template response and 0.8% higher image RMS than `wide`. It can remove
true weak detail and most actual mask solves hit the 8192-step cap; metadata
records gaps/caps. Clipped windows and small-image fallbacks retain their earlier
behavior. These phase options are exposed by `infer`, not the DNG batch exporter.

Add `--self-ensemble dihedral8` to `infer` for optional eight-view quality
inference. It preserves Bayer geometry and averages camera-RGB predictions
before tile blending and RGB16 export, requiring eight model evaluations per
tile. `benchmark`, `quality` and the DNG batch exporter accept the same option; receipts
record the policy. [Measured gains, native comparisons and remaining limitations](dihedral-quality.md).
The [completed full 102MP RGB16 review](dihedral-fullframe.md) includes native
foliage/fence comparisons and the actual FP32 inference observation. Broader
eight-view V104 quality panels and independent checks are complete, with measured
photo/camera gains and remaining color/detail tradeoffs. V112 has a separate
[fixed24 pilot](v112-eight-view.md). The [current V114 fixed24 result](v114-eight-view.md)
improves all12 material cases and both selected camera crops, with a small
selected color-bias tradeoff. Full V114 eight-view panels/frame remain unmeasured.

For reproducible real-capture comparisons, `scripts/report_raw_pair.py` accepts
`--noise-profile profile.json`. It supports the `demosaic noise-profile` wrapper
(`estimate` plus optional `raw_metadata`) or a direct reliable estimate with
finite, nonnegative `shot` and `read`. Camera/ISO metadata, when supplied, must
match the noisy capture. The report archives the exact supplied bytes and records
that the estimator was skipped. Fixed historical coefficients are a comparison
convention, not newly verified camera calibration. Omitting the option retains
automatic input estimation and its nominal-prior fallback.

### Repeating mesh crops

The experimental carrier fits are available through
`demosaic.mesh_carrier_fit.refine_raw_mesh_carriers` with the `eval` extra.
The callable refines a 160×160 linear camera RGB crop using the same
exposure's native Bayer measurements. The pooled options use a 16-pixel
halo of restored RGB to estimate what the parent already recovered. They
use the surrounding 192×192 RAW region to estimate carrier phase and
check each proposed correction on held green samples. All three fits
use four nearby 128-pixel RAW donor patches. Weak or incomplete
donor support returns the input crop.

```python
from demosaic.cfa import PATTERNS
from demosaic.mesh_carrier_fit import refine_raw_mesh_carriers

x, y, size, halo = 1026, 6449, 160, 16
refined = refine_raw_mesh_carriers(
    camera_rgb[:, y:y + size, x:x + size],
    packed_bayer,
    PATTERNS[metadata.pattern],
    (x, y, size, size),
    shot=shot,
    read=read,
    white_balance=metadata.white_balance,
    camera_to_srgb=metadata.camera_to_srgb,
    method="pooled-color",
    parent_context=camera_rgb[:, y - halo:y + size + halo, x - halo:x + size + halo],
)
```

`camera_rgb` is the restored RGB in unrotated sensor coordinates and
`packed_bayer` has shape `[4, H/2, W/2]` in top-left, top-right,
bottom-left, bottom-right order. The example coordinates identify the
standing right cab crop. Use `method="pooled"` for the green-only fit
with the same context. `pooled-color` adds nearby red and blue phase
evidence and tests both directions when rank is ambiguous. It still
delivers a neutral correction, which can distort strand color when the
channels have different phase. The original 64-pixel fit is the default
`method="local64"` and uses just the 160×160 parent.
Use `method="ring-posterior"` with `parent_context=None` for
the ring phase prior. It estimates weak support in the center
from both green lattices and the surrounding RAW ring.
Use `method="weak-posterior"` with the 192×192 `parent_context`
shown above to apply that prior only to the weaker direction.
For repeating mesh with coherent surrounding phase, `method="weak-phase-guard"`
uses the same inputs and tapers that additional weak correction using local
RAW evidence. [Results and timing](local-phase-extent.md#packaged-crop-fit).
`method="weak-phase-contrast"` uses the same inputs, with full fitted strength
on the same admitted windows when the surrounding phase is reliable. It recovers
more faint contrast on exact targets, with some increase in gap texture. [Results and timing](local-weak-contrast.md#packaged-crop-fit).
`method="weak-near-phase"` uses the same inputs and pools the immediately
surrounding 32 pixels when distant phase fails. It checks that predicted phase
inside the existing weak windows. [Results and timing](local-near-phase.md#packaged-crop-fit).

`method="weak-replicated-phase"` uses the same inputs. When green rank is
ambiguous it checks both directions with two-green and along-wire support.
The local station limits the strength delivered to its pixels. [Results and timing](local-replicated-phase.md#packaged-crop-fit).

`method="weak-internal-phase"` uses the same inputs. It pools phase inside
the crop, excluding the test station and its neighbors from the phase
estimate. The additional check applies when rank is ambiguous or distant
phase is unreliable. [Results and timing](local-internal-phase.md#packaged-crop-fit).

`method="weak-junction-phase"` also tests a signed difference-frequency
term and limits it to stations with both wire directions. This mode
requires a 48-pixel halo. Set `halo = 48` in the example to supply a
256×256 `parent_context`. [Results and timing](local-junction-support.md#packaged-crop-fit).

[Regional color results and timing](cfa-regional-phase.md#packaged-crop-fit) ·
[Green-only pooled results](local-pooled-carrier.md#packaged-crop-fit) ·
[Ring prior results and timing](local-bayer-presence.md#use-the-crop-option) ·
[Weak-only results and timing](local-conditional-posterior.md#use-the-crop-option) ·
[Original 64-pixel fit](bayer-carrier-scale.md).

## Environment and storage

For native RGB16 DNGs plus full-resolution JPEGs from RAW/XMP pairs, use the
[batch DNG exporter](dng-export.md). It records noise conditioning and hashes,
and retains adapted darktable edits alongside the restored camera-linear data.

Run commands from the repository root after `source scripts/env.sh`. This keeps
uv, Hugging Face, Torch, compiler caches and temporary files inside the repository.
Large generated data and runs belong in `/mnt/external/demosaic`. Source photo
directories and Commons originals are read-only for ingestion; the authorized
[background downloader](commons-download.md) adds verified archive files.
Output APIs reject
writes outside this repository and `/mnt/external`, and reject the Commons source.
Do not run environment/setup commands without the cache environment.

## Commons preparation

`demosaic prepare --output /mnt/external/demosaic/commons-v1 --limit 1024`
queries a short read-only SQLite metadata snapshot, including committed WAL data
while the downloader runs. It accepts CC BY,
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
the frozen audit appropriate to each experiment. V28–V30 use all 40,170 training
sources in this 44,732-source audit. [The optional 4×→2× augmentation path](training-pipeline.md)
rebins a frozen selection without changing its protected membership and retains
the original 8× validation manifest.

For an additional camera-linear target source prepared directly from licensed
low-ISO Bayer captures, see [native RAW targets](native-raw-targets.md).

## Training

`demosaic train configs/base.yaml` starts the no-foundation baseline.
`configs/dino.yaml` explicitly enables a frozen pretrained DINOv3-S/16 branch;
access errors are not replaced with random weights. Both use the same restoration
architecture. The foundation backbone is excluded from EMA/optimizer copies and
restoration checkpoints; it is loaded independently from its named HF source.
Run environments must retain the matching backbone and its license.

The [V28 pretrained restoration experiment](pretrained-rgb-restoration.md) adds
an opt-in native RGB trunk with verified Gaussian restoration initialization,
CFA/camera conditioning and frozen DINOv3 context. Its [5k review](pretrained-rgb-v28-5k-review.md)
and [matched calibrated stabilized trial](anchored-stabilized-rgb-v30-review.md)
record progress and remaining quality deficits; existing model defaults remain
the local restoration backbone. Mixed training now loads only the selected
domain instead of preparing discarded Commons batches; see [pipeline validation
and the batch-size sweep](training-pipeline.md).

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

Optional `reconstruction_objective: image-log-mse-v1` replaces the primary
synthetic linear/rendered and paired measured-CFA/coarse-rendered penalties
with per-image negative PSNR, using the existing validity masks. Auxiliary,
gradient and highlight penalties retain their definitions and coefficients;
relative gradient scales change. The default is `charbonnier-v1`. Resume rejects
a changed objective. This training-only option has engineering checks but no
demonstrated quality gain; see [the bounded matched trial](reconstruction-objective-v74-v75.md).

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
in estimated-noise units. The branch defaults to IEEE FP32 arithmetic even when the
base network uses BF16/FP16. Optional inference flag
`--refinement-precision float16` accelerates only its neural operations; physical
noise/high-pass/scaling operations remain IEEE FP32. CPU execution stays FP32,
and training is unchanged. See [validation and native crops](refinement-precision.md). With `refiner_only: true`, only that branch trains;
all original restoration/DINO parameters are frozen. Changing that trainable
selection on resume is rejected. The photo-trained V15 recipe is
`configs/dino-paired-refiner-v15.yaml`; its frozen step5000 evaluation improves
real RAW development quality, but it is still behind RawNIND. Flat-only V14 is
rejected. See [the review and native crop comparisons](photo-refinement-review.md).

The larger `configs/dino-paired-refiner-wide-v16.yaml` has completed its 5000-step
review. Its historical crop evidence remains available; the README follows the
[current model choices](current-model.md). V16 remains behind RawNIND on
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

`quality --self-ensemble dihedral8 --precision float32` evaluates eight-view
checkpoint predictions on the same observations. References keep one view;
report labels and provenance identify the policy. The prepared-camera Python
entrypoint `real_suite.evaluate_pairs` and the texture/color evaluation scripts
accept the same policy. [Full comparison scope and current results](dihedral-quality.md).

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
New metadata-backed fits distinguish the true ADC floor from valid negative
black-subtracted samples; narrow-range shadow crops can still be rejected.

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
For Corpus 100k on the GB10, use `--precision float16`. Tiled restore on
the 102 MP GFX frame falls from 287.38 to 53.40 seconds versus IEEE FP32.
Weak-wire response and the native GFX crops stay visually close to FP32.
[Full RGB16 differences and fixed quality panels](corpus100k-mixed-precision.md).
Use `--tile 512 --overlap 64 --batch-size 4` to reproduce that geometry.
`--batch-size 2` lowers peak PyTorch CUDA allocation from 2.12 to 1.24 GB
on the 102 MP frame, with similar speed and small RGB16 differences.
Eager batch eight takes the same time as batch four and uses 76% more
PyTorch CUDA memory in the paired replay.
[Batch size and compiled timing](corpus100k-fp16-batch.md).
Larger tiles with less overlap change some clipped colors. With 512-pixel
tiles and the compiled FP16 engines, reducing overlap alone to 32 also
produces larger changes around bright lights and seams.
[Tile settings and native evidence](corpus100k-fp16-throughput.md) ·
[Fixed-size overlap comparison](corpus100k-overlap.md).
Device-resident blending and CUDA Graph replay take about the same time
on 102 MP and roughly double peak CUDA allocation.
Full-frame cuDNN search in FP16 gives no repeatable gain. Use the
standard FP16 command for Corpus 100k.
[CUDA tile transport](corpus100k-device-tiles.md) ·
[FP16 full-frame autotuning](corpus100k-cudnn-fp16.md) ·
[Compiled DINO prototype](corpus100k-trt-dino.md).

CUDA `infer` uploads the checkpoint from pinned CPU memory when available.
The sidecar reports `checkpoint_setup_seconds`. In the paired Corpus 100k
run, checkpoint setup takes 2.52 s versus 52.59 s and both RGB16 TIFFs are
identical. [Cold-start and TensorRT measurements](corpus100k-faster-inference.md).

For CUDA FP32 inference, optional `infer --cudnn-benchmark --precision float32`
searches convolution algorithms with a limit of 10 and a 16GiB PyTorch CUDA
allocator cap, retaining any stricter existing quota. Refinement must also stay
FP32; checkpoints forcing hidden half precision are rejected. The helper restores
prior backend settings, precision and quota on exit/error. The flag defaults off;
the sidecar records its effective settings. It does not change training or the
separate `benchmark` command, clear algorithm caches, or cap all unified RAM.

On the cached 102MP GFX scene, the actual fresh V43 CLI restore takes166.67s
including search. A separate warmed comparison takes206.88→118.22s with every
unquantized value within the original1DN16 max/.25DN16 RMS limits. These timings
have different startup scopes; see [the full report, RGB16 checks and native crops](mature-cudnn-fullframe.md).

FP16 gives a small measured quality gain for V6: a matched 427-photo comparison
finds +0.0218 dB and +0.000723 SSIM over BF16. The 16-photo FP32 reference is
close to FP16. Use the explicit flag when reproducing those V6 results. Neither half-precision option makes the learned feature
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

Experimental `model.pyramid_refinement: true` adds a two-level correction network
with direct measured-CFA innovation. `pyramid_measurements: false` supplies zeros
to those channels for a capacity-matched control. `pyramid_refiner_only: true`
freezes every preceding restoration/DINO/fine/coarse parameter and trains only
that branch; it cannot be combined with other refiner-only modes or changed on
resume. Existing checkpoint defaults remain disabled. See
[the matched experiment and startup validation](pyramid-refinement.md); the first 1000-step review does not establish a real-photo quality gain.

`multiscale_sensor_weight` optionally adds pooled measured-CFA reconstruction
in input-noise units at 8/32/64 sensor-pixel footprints to both synthetic and
paired training. Its default is zero. The value must be finite and nonnegative
and cannot change on resume. Reference masks exclude incomplete/clipped blocks
and ADC-only inputs; physical arithmetic stays IEEE FP32. See
[the matched supervision experiment](scale-aware-supervision.md). The new term
is a training objective, not a posterior-noise calibration or an established
quality improvement.

`normalization_augmentation: center-half-mix-v1` enables the optional
[normalization-coordinate training augmentation](normalization-augmentation.md)
for stabilized, anchored, full-resolution RGB models. Its default is `none`.
It changes only selected images' feature-coordinate statistics, preserving RAW,
targets and DINO inputs without extra neural forwards or RNG consumption. The
policy is logged and cannot change on resume. Ordinary inference retains full
context normalization. CPU engineering checks pass; trained quality and CUDA
validation remain pending.

Optional `--gaussian-reference /path/to/verified-receipt.json` on `quality`,
`scripts/evaluate_paired_raw.py` and `scripts/report_raw_pair.py` evaluates a
frozen Gaussian denoising prior with physical variance stabilization. The
reference receipt pins external source/weights; each report archives them.
No evaluation-image fitting or target-derived gain is used. This comparator
is experimental and has substantial photographic limitations; see
[the method and native-crop review](stabilized-gaussian-review.md).
