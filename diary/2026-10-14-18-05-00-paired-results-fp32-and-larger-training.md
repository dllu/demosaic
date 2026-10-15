# Paired results, numerical precision, and larger training

Both matched 8192-source runs completed 20000 steps. Full validation uses 427
photos, 16 separate synthetic examples, four CFA phases, and seven declared
noise/exposure cases. The DINO branch adds 0.0534 dB rendered PSNR over its
control, source-bootstrap 95% interval 0.0426–0.0659; SSIM increases 0.00377.
This is a small benefit under this protocol, not state-of-the-art evidence.

Overall rendered PSNR/SSIM: DINO 29.0946/0.85265, control 29.0412/0.84888,
bilinear 27.5548/0.81170, white-balanced Malvar 28.5386/0.83952, RawNIND with
global CFA gain 26.6708/0.78717, per-channel CFA gain 26.6586/0.78703.
Stronger input-only reference gain fitting does not close the aggregate gap.
Important failures remain: shadows favor RawNIND in both metrics; high-noise
SSIM favors RawNIND; low-noise and highlight SSIM can favor Malvar. No broad
qualitative superiority claim is justified. Private RAW comparisons also show
more residual grain in our early model. Test images remain untouched.

The warmed 20k DINO 100 MP restoration takes 14.528 s with 0.803 GB allocated
CUDA memory, excluding RAW decode/load/encode. This misses the 10 s target.
Earlier 9.34 s non-DINO timing is historical and uses the old precision path.

Found an avoidable numerical issue: autocast rounded the bilinear residual
baseline, with checked maximum error 0.00553 versus float64. New physical
interpolation/color paths explicitly disable autocast and TF32 while keeping
cuDNN enabled. The same FP32 interpolation check differs by only 5.96e-8.
Old checkpoints preserve their original mode; current loading reproduces the
archived 20k inference bit-for-bit. All 43 tests and lint/format checks pass.
Current suite runs archive evaluation code, manifest, protocol and weight hashes.
Older suite artifacts retain their original code hashes and precision conventions.

The 24576-source frozen audit excludes one training-linked validation duplicate:
22059 train, 1262 validation, 1254 test, one excluded. This fingerprint screen
does not prove complete scene separation. Broader 8×8 preparation remains live,
with more than 39000 licensed sources already processed, without changing inputs.

Started `/mnt/external/demosaic/runs/dino-noise-24576-v4`, fresh 100000-step
schedule initialized from DINO 20k EMA. It uses IEEE FP32 physical operations
and identity-initialized multiscale log-variance modulation, with 20% procedural
training draws. Its first checkpoint at 1000 steps passed balanced validation;
peak training allocation is about 1.02 GB. Exact source/protocol/manifest snapshots
are inside the run. Selection uses 16 native validation crops across 28 cases,
rather than relying on the old single-condition diagnostic. This experiment
changes several factors and is not a matched noise-modulation ablation.

Logs: `.cache/train-dino-noise-24576.log` and `.cache/prepare-all.log`.
Full comparison: `/mnt/external/demosaic/evaluation/paired-20k-reference-gains-v2`.
Remaining work includes larger-run quality, calibrated real-camera detail/noise
review, current-precision 100 MP/end-to-end measurements, and a stronger current
baseline before any state-of-the-art or final completion claim.
