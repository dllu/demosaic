# RAW feature coordinates from a fresh start

The [completed CPU diagnostic](results/packed-isotropic-fresh-coordinate-CPU-v1.json)
uses the same16 frozen training batches as the earlier
[production-learning checks](packed-isotropic-production-learning.md).
All three arms completed256 updates and discarded learned weights. Starting
parameter bytes and Torch RNG match, and initial predictions equal the same
bilinear baseline on all16 batches. Neither alternative input map gives a broad
improvement: every final original-domain loss exceeds initialization, and all
three arms worsen paired measured-CFA MSE.
The separate [completed CUDA residual-unit diagnostic](packed-isotropic-residual-units.md)
uses four actual GPU controls and does not replace this CPU experiment.

The question is whether weak RAW features relative to the conditioning features
make learning difficult. The earlier gain 4 experiment scaled RAW inputs and
divided their stem weights, preserving the internal values. Here the starting
weights stay common while the input representation changes. The zero-initialized
output head preserves a common initial prediction despite different activations.

| Arm | Four RAW input features |
| --- | --- |
| `raw` | Original normalized camera-linear measurements |
| `gain32` | Original measurements multiplied by 32, with the common stem initialization |
| `noise-compand` | Pointwise companding using the supplied shot/read coefficients |

The compander maps sensor values 0 and 1 to 0 and 1, extends negative values linearly
with a smooth join at zero, and is monotonic. Gaussian-only and ADC-only inputs
retain their original coordinates. It uses the supplied noise parameters without computing
crop normalization statistics. It changes the signal features entering the neural stems;
the physical RAW skip and camera-RGB prediction/loss units remain fixed. The
four variance features and 24 CFA/WB/matrix features retain their original values.
There is no inverse transform at the output. The implementation is isolated in
[the diagnostic script](../scripts/probe_raw_feature_coordinates.py). This
experiment retained frozen model modules and changed no production recipe.
The subsequent [checkpointed unit options](packed-isotropic-units.md) keep
defaults1 and do not change this diagnostic or its source.

## Actual samples and optimization

The 16 observations came from production steps 8001–8016 at batch4/native256:
seven Commons/procedural batches, four native-RAW synthetic batches and five
paired-RAW batches. Their 64 retained examples and noise draws are reused
identically by all arms. This is a repeated small training set, with the existing
training split and no held-out/GFX/protected-final optimization.

Each no-DINO model is constructed fresh with seed 51 and the original width 96,
six groups/eight blocks/local width 32. The three models begin with identical capacity
and parameter bytes. Each uses fresh AdamW, LR 2e−4, weight decay .01 and gradient
clip 1, with256 completed updates. Those repeat the same16 batches16 times; no
production warmup, schedule, continuation or convergence claim follows.

The original domain losses remain in physical units. Synthetic reconstruction
uses the fixed clean target. Paired detail error uses only valid measured
reference-CFA samples; independently demosaiced RGB contributes only its
existing coarse loss. A low-ISO reference retains noise and is not exact RGB GT.
Whole-fixture losses/MSE are measured at 0, 64, 128 and 256 updates, with descriptive
batch means per domain. These training errors do not measure generalization.

## Completed256-update result

Each cell is **original-domain loss / MSE**, divided by the common initial
full-fixture value. Lower is better; these are training errors.

| Input coordinates | Commons/procedural | Native RAW synthetic | Paired measured CFA |
| --- | --- | --- | --- |
| Original RAW | 1.05540 / .94112 | 1.13319 / .98223 | 1.13536 / 1.10534 |
| RAW ×32 | 1.07844 / .90006 | 1.16763 / 1.02082 | 1.24715 / 1.10929 |
| Noise companding | 1.06916 / .97295 | 1.11437 / .99089 | 1.22940 / 1.09693 |

Gain32 lowers Commons MSE more, but worsens native and paired MSE against the
initial prediction. Companding offers no broad loss/MSE advantage. These fixed
observations, constant LR and short horizon do not establish convergence or
generalization, and no input-only map is adopted from this result.

Independent replay verifies768 ordered finite training records, all72 domain
mean reductions with `math.fsum`,19 inputs and42 guards. All852 Adam states
per arm are finite at256, original batch fingerprints are unchanged, CUDA was
never initialized, and the exact CPU owner exited. Common initial model SHA256
is`ed1fdca69f4568ffc4c687db6f6677703c8f1b8203353975dd56476f74cc378d`;
Torch RNG SHA256 is`9e2d4112a0b8384c304c4c7a38b5b2c11ddadd7b1d88a68b1920c4c6abed80c0`.
The [launch plan](results/packed-isotropic-fresh-coordinate-CPU-launch-v1.json)
and interim64 evidence remain unchanged.

## Archived interim64 comparison

The [independently audited interim receipt](results/packed-isotropic-fresh-coordinate-CPU-interim64-v1.json)
retains immutable copies of the evaluation curves and first 192 update records.
The table reports **64-update / initial MSE**, so values below one indicate
lower error against the same fixed training observations and targets.

| Input coordinates | Commons/procedural | Native RAW synthetic | Paired measured CFA |
| --- | ---: | ---: | ---: |
| Original RAW | 0.94225 | 0.98892 | 1.16459 |
| RAW ×32 | 0.93168 | 0.91761 | 1.26103 |
| Noise companding | 0.98316 | 1.00556 | 1.15152 |

Gain32 lowers native synthetic MSE more, but worsens paired MSE. Companding
does not offer a broad reduction. All nine domain/arm loss ratios exceed one
at this point. This is a short fixed-LR fresh-model diagnostic with repeated
samples; it does not show convergence or establish a final ranking.

Gradient clipping occurs on 55/64 original-RAW updates, 64/64 gain32 updates
and 57/64 companded updates. These are observed global pre-clip norms, not a
controlled clipping ablation or proof of a failure mechanism. The independent
auditor rechecks all 61 source/input hashes, the exact live process identity,
all update/mode/observation ordering and finite losses/norms, and recomputes all
36 domain means with `math.fsum`. They agree exactly with the saved reductions.
Initial case losses/MSE are identical across arms; the original worker's actual
all-batch bilinear equality checks and common model/RNG digests remain recorded.

The diagnostic subsequently completed its original256 updates, yielding to
owned review/timing jobs as planned. Neither the interim nor the final result
supports a production input-coordinate change or a new quality model.

## Execution checks and scheduling

Seven focused tests pass, including signed/monotonic inputs, one-code 16-bit
changes, zero-shot identity, crop/per-example independence, smooth positive
gradients, FP32 under outer AMP, and actual all-CFA initial-signal preservation.
The prototype hook restores the original feature function even on an exception.
Ruff checks pass. Actual execution verifies all 16 observation fingerprints and
retains the first 48 update records, covering all three arms' first full cycle.

The common initial model tensor digest is
`ed1fdca69f4568ffc4c687db6f6677703c8f1b8203353975dd56476f74cc378d`.
This hashes tensor names/bytes, rather than a saved checkpoint. The worker
discards learned states at exit; none becomes a quality initializer or portable model.

CUDA is hidden and Torch uses two CPU compute threads. After the original
training owner exits, this worker yields before each forward/update while any
exact owned review/timing controller or its final child is alive. This keeps
the queued GPU measurements free of this owned CPU workload. Sources, arrays,
code snapshots and the actual running process are bound by the launch receipt.

Live status:
`/mnt/external/demosaic/runs/packed-isotropic-fresh-coordinate-CPU-v1.json`.
The matched 40k trials and subsequent full-quality/compilation/corrected-grid
reviews continue independently. This diagnostic supplies no new quality model
or decision to change their recipes.
