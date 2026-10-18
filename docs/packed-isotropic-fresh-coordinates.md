# RAW feature coordinates from a fresh start

The [CPU diagnostic](results/packed-isotropic-fresh-coordinate-CPU-launch-v1.json)
is running on the same 16 frozen training batches used by the earlier
[production-learning checks](packed-isotropic-production-learning.md).
All three arms have completed their first 16 optimizer updates. Their starting
parameter bytes and Torch RNG match, and every initial prediction equals the
same bilinear baseline on all 16 batches. Final learning comparisons are pending.

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
[the diagnostic script](../scripts/probe_raw_feature_coordinates.py); production
model modules and recipes are unchanged.

## Actual samples and optimization

The 16 observations came from production steps 8001–8016 at batch4/native256:
seven Commons/procedural batches, four native-RAW synthetic batches and five
paired-RAW batches. Their 64 retained examples and noise draws are reused
identically by all arms. This is a repeated small training set, with the existing
training split and no held-out/GFX/protected-final optimization.

Each no-DINO model is constructed fresh with seed 51 and the original width 96,
six groups/eight blocks/local width 32. The three models begin with identical capacity
and parameter bytes. Each uses fresh AdamW, LR 2e−4, weight decay .01 and gradient
clip 1, with 256 planned updates. Those repeat the same 16 batches 16 times; no
production warmup, schedule, continuation or convergence claim follows.

The original domain losses remain in physical units. Synthetic reconstruction
uses the fixed clean target. Paired detail error uses only valid measured
reference-CFA samples; independently demosaiced RGB contributes only its
existing coarse loss. A low-ISO reference retains noise and is not exact RGB GT.
Whole-fixture losses/MSE are measured at 0, 64, 128 and 256 updates, with descriptive
batch means per domain. These training errors do not measure generalization.

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
