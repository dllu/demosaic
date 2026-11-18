# Training across the near-ADC noise gap

The [86k noise audit](noisy-cfa-residual.md) found no positive training
prior below about 156 ADC codes RMS at full signal. On the held-out
near-ADC tests, small positive conditioning produced large flat-color
errors and attenuated weak detail. The bounded measurement correction
helped at the smallest tested prior. A matched continuation now tests
whether exposure to the missing noise range improves the learned
prediction itself.
[Locked recipes and live dispatch receipt](results/near-adc-bridge-training-v1/publication.json).

Both 800-update training runs are complete. The matched native and
faint-detail evaluations are collecting.
[Completed checkpoint and training audit](results/near-adc-bridge-training-v1/completed-training.json).

## Matched training

Both arms initialize all restoration weights from the
[completed 100k trajectory](full-corpus-long100k.md) EMA checkpoint.
Each arm uses fresh AdamW state and completed 800 updates
of 16 native 256×256 patches, or 12,800 example slots. The schedule uses
a 40-update warmup and peak learning rate of 0.000003. The architecture,
restoration loss, photo and RAW readers, random exposure, source order,
and validation protocol are shared.

A fresh seeded order draws from the same 90,778 eligible ordinary
photographs. The planned source schedule contains 4,325 unique ordinary
photo visits, 408 Commons batches, 192 native-synthetic batches and 200
measured paired batches. Photos that appear in multiple project runs
may still occur in this order. The original 100k trajectory and its
source order are separate.

The candidate resimulates about half of the original ADC-only examples in
the Commons and native-synthetic domains. Each replacement draws a
log-uniform full-signal standard deviation of 4–160 codes and a
log-uniform read-noise value of 0.7–1,500 electrons. With full-signal
variance `v` and read noise `e` in electrons, the shot coefficient is
the positive solution of `shot + (e * shot)^2 = v`. Read variance is
`(e * shot)^2`. The generator uses the recorded black level and samples
the original clean camera signal through the existing Poisson/read/ADC
operator. Exposure, CFA, WB, matrix and clean targets stay matched.
All original positive-noise and measured paired examples use their
original observations. Private GFX captures and their siblings stay
outside the existing training manifests.

The implementation is available through the training configuration
`near_adc_bridge_fraction`. Its range is 0 to 1, and the default is 0.
Resuming requires the same fraction. Profile choices and new sensor
draws use their own deterministic generators.
[Training integration](../src/demosaic/train.py) ·
[Sensor augmentation](../src/demosaic/near_adc_training.py).

## Executed data preflight

The first 32 native-size batches were read with the actual training
readers on CPU. Their 512 slots cover 14 Commons, 11 native and seven
paired batches. Independent regeneration exactly reproduces the 23
replacement Bayer observations. All untouched values and the clean
targets match, including the paired observations. Selected values
span the ranges recorded in the machine receipt. This stage exercises
the input pipeline before model initialization or training.
[Actual inputs and reproducibility](results/near-adc-bridge-training-v1/data-preflight.json).

The full reconstruction loss and backward pass were then exercised
on the lowest-noise and highest-read-noise admitted samples, using
the retained 86k EMA on CPU. Both losses and all 89 trainable
gradient tensors were finite. The smoke test took no optimizer
updates.
[Gradient smoke and executable receipt](results/near-adc-bridge-training-v1/gradient-smoke-publication.json).

## Completed training audit

| Arm | Retained checkpoint SHA256 | Training loop seconds |
| --- | --- | ---: |
| Control | `925a62a9e78af94469354752b8cd767c9e89e1dbe2785bfa5a841e46804a0346` | 637.34 |
| Near-ADC | `42c5cc828c38d6c79aa40424735a05b428de01814010f0f3c6f8723117c6ec63` | 642.80 |

Both checkpoints contain raw and EMA weights, complete Adam state
and CPU/CUDA/Python RNG state. Evaluation uses the EMA from each
checkpoint. The common parent is the immutable 100k EMA
`87b96f3c487b9edaf1c477742b6c38f2a82cc6b20a94716d51cc8cf46a17a760`.
Each run consumes 12,800 slots over 408 Commons, 192 native
simulation and 200 paired RAW batches. Its measured worker-loop
duration includes its validations and saves. The two runs share
bit-identical source/crop traces and camera metadata.

The near-ADC arm changes **483 of the original 980 ADC-only slots**,
330 Commons and 153 native simulation. Reconstructing the profile
draws gives 4.02–158.11 ADC codes full-signal RMS and 0.70–1,488.97
electrons read noise. Converting the measured normalized variance to
ADC codes includes the camera's sampled black level.
[Realized condition audit](results/near-adc-bridge-training-v1/training-audit.json) ·
[ADC units and profile selections](results/near-adc-bridge-training-v1/conditioning-units.json).

The initial launcher pointed outside the frozen working directory
and stopped before any training update. The corrected control
continued through a launch receipt collision. A stale path in the
following post-training audit briefly delayed evaluation. The
recovery bound both original completed checkpoints and started
the pending reviews.
[Launch recovery](results/near-adc-bridge-training-v1/launch-recovery.json) ·
[Completed endpoints and post-training recovery](results/near-adc-bridge-training-v1/completed-training.json).

## Quality review

The evaluation workers are collecting the 110 existing native inputs
with both standing GFX scenes. They also compare the parent and both
train branches on exact faint-photo, flat and edge inputs. They use
the same CPU IEEE FP32 policy and verified saved V120 and parent
controls where the observations match.

Numerical review and actual native inspection are pending.
The canonical 427-photo and known/unseen camera review is queued for
the CPU allocation after the 20k corpus control finishes collecting.
The latest evaluated parent remains the 100k EMA. The matched noisy
and exact-target panels use the same reductions as the previous
near-ADC study. Their scorer exactly replayed all 512 prior saved
photo rows and 128 flat/edge rows before seeing the new outputs.
[Parent native report](full-corpus-long100k.md) ·
[Comparable PSNR history](performance-history.md).
