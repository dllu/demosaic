# Training across the near-ADC noise gap

The [86k noise audit](noisy-cfa-residual.md) found no positive training
prior below about 156 ADC codes RMS at full signal. On the held-out
near-ADC tests, small positive conditioning produced large flat-color
errors and attenuated weak detail. The bounded measurement correction
helped at the smallest tested prior. A matched continuation now tests
whether exposure to the missing noise range improves the learned
prediction itself.
[Locked recipes and live dispatch receipt](results/near-adc-bridge-training-v1/publication.json).

## Matched training

Both arms wait for the existing 100k trajectory to finish successfully,
then initialize all restoration weights from its immutable EMA
checkpoint. Each arm uses fresh AdamW state and completes 800 updates
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

The candidate resimulates half of the selected ADC-only examples in
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

## Quality review

After both checkpoints close, an evaluation job will collect the
110 existing native inputs with both standing GFX scenes and compare
the parent and both train branches on exact faint-photo, flat and
edge inputs. It will use the same CPU IEEE FP32 policy and verified
saved V120 and parent controls where the observations match.

The 100k parent and both training endpoints are pending at this
publication cutoff. Numerical review, actual native viewing and
the canonical 427-photo plus known/unseen-camera evaluation close
separately. The latest evaluated long-run checkpoint is 86k.
[Parent run and endpoint review](full-corpus-scaling.md) ·
[Comparable PSNR history](performance-history.md).
