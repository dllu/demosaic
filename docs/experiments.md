# Experiment evidence

All numbers below are local observations on the NVIDIA GB10, not reproduced
paper results. The project has not passed its final quality gate.

## Bootstrap, October 14, 2026

`configs/bootstrap.yaml`: 4,328,700 parameters, 1000 steps, batch 8, 256 sensor
pixels, BF16. 237 photographic training sources plus 20% procedural draws.
Initial validation comprises 13 source-disjoint images. Peak CUDA allocation
1.498 GB; 0.118 s/step including initial warmup and checkpoint work. At step 1000,
linear/rendered PSNR is 36.343/32.981 dB versus bilinear 35.893/32.452 dB.

The expanded, immutable 1024-source manifest contains 925 train, 61 validation,
38 test sources. **Test images remain unused for model selection.** The bootstrap
network was evaluated on all 61 validation sources at shot=0.001, read=1e-6,
fixed WB [2,1,1.5], identity color matrix, RGGB, and a fixed noise seed:

| Method | Camera-linear PSNR | Rendered PSNR |
| --- | ---: | ---: |
| Noisy bilinear | 36.017 | 31.765 |
| Bootstrap, 1000 steps | 36.617 | 32.381 |
| RawNIND UtNet2, input-mean gain | 29.818 | 26.807 |
| RawNIND UtNet2, CFA least-squares gain | 33.756 | 28.914 |
| Highlight-v2, 5000 steps, 925 train sources | 37.216 | 32.857 |

This is one synthetic condition close to our training distribution. It does not
prove real-camera generalization, perceptual superiority, or state of the art.
RawNIND used the authors' Bayer weights at iteration 4,350,000 in FP32, exact
upstream UtNet2, normalized input and no WB before inference. The published
darktable demo's input-mean gain can be biased because green is counted twice in
the Bayer mean. CFA least-squares matches reconstructed sensor samples to the
observed mosaic, without target access. We report both rather than relying on
the weaker calibration. Provenance and SHA hashes are recorded by the download
script; reference outputs still need qualitative review and more conditions.

Artifacts: `/mnt/external/demosaic/evaluation/bootstrap-vs-rawnind-val61.json`,
`/mnt/external/demosaic/runs/bootstrap-v1/`, and
`/mnt/external/demosaic/references/rawnind/`.

## Size and speed

Real 10000×10000 restoration, 512 sensor-pixel tiles, overlap 64, batch 8:

| Implementation | Measured seconds | Peak allocated CUDA GB |
| --- | ---: | ---: |
| Initial NCHW tile loop | 13.631 | 0.722 |
| Channels-last weights, old host packing | 10.732 | 0.722 |
| Channels-last + per-batch device packing | 9.878 | 0.722 |
| Trained highlight-v2, SIMD input validation | 9.341 | 0.747 |

The final row includes validation/host accumulation/normalization and avoids a
second full-image Bayer packing allocation. GPU kernels were warmed. It excludes
RAW decode, checkpoint loading and TIFF encoding. Timing includes process noise;
repeat idle measurements and the final trained network are still needed. See
`/mnt/external/demosaic/benchmarks/` for machine-readable records.

These measurements use the original interpolation precision. The completed
20k-step DINO model takes 14.528 s for the same warmed 100 MP restoration
(13.302 s in its tile loop), with 0.803 GB peak allocated CUDA memory. It misses
the 10 s target. Neither this timing nor the earlier 9.34 s result measures RAW
decode/load/TIFF encoding. The new FP32 model needs a new speed measurement.

A real GFX100S RAF produced 8746×11662 RGB16 TIFFs in camera-linear and sRGB
forms without modifying the source. Its cold restoration took 17.043 s, including
kernel startup. This older invocation did not measure complete decode/encode
latency. Inspection caught a matrix-direction bug, now fixed against LibRaw
`cam_xyz_coeff`, and pink saturated highlight artifacts. The restored image is
an experiment, not a final-quality output.

## Highlight target correction

`base-v1` continued bootstrap weights on 925 sources. It was stopped after a
verified step-500 checkpoint when visual review showed that independent
camera-channel clipping made its target itself color biased after WB/matrix
conversion. Only our own training process was interrupted; its weights remain.

`highlight-v2` adds WB and camera-matrix conditioning, and builds bounded clean
references by clipping linear sRGB before transport to camera space. The noisy
input still experiences physical per-channel sensor clipping. This gives neutral
reference highlights without making up saturated detail. A regression test proves
the target correction; it does not prove the trained network has learned it.
This run uses the initial camera-space highlight mask and ADC black=0. At step
3000, a controlled neutral highlight with diagonal fine lines reduced highlight
chroma MAE from bootstrap's 0.015744 to 0.005378 (about 66%). Rendered PSNR
improved 34.646→34.943 dB. The diagnostic figure was inspected: the main magenta
cast is suppressed, but small color errors remain on fine lines. This is one
synthetic case; real highlight quality remains unproven. Artifacts are in
`/mnt/external/demosaic/evaluation/highlights-v2/`.

`highlight-v3` adds a rendered-space highlight mask and an ADC black offset so
negative black-subtracted read noise survives. New runs archive the actual source
code/lockfile and manifest SHA. These changes need trained-model validation and
comparison with v2. The v3 config is available; its training is not yet established
by this document.

## DINOv3 and matched broad-data experiments

Access became available later on October 14. The genuine DINOv3-S/16 branch
passed a CUDA BF16 forward/backward check with a nonzero fusion-gate gradient
and a frozen 21,596,544-parameter encoder. Revision
`114c1379950215c8b35dfcd4e90a5c251dde0d32` is pinned. A step-1500 restoration
checkpoint reloaded and produced finite predictions while loading its encoder
separately, verifying the checkpoint contract with real weights.

The immutable 8192-source manifest contains 7378 train / 427 validation / 387 test
sources. `configs/dino-8192.yaml` and `configs/control-8192.yaml` use the same
data, batch size, seed, 20000-step schedule, degradation and highlight-v2 EMA
initialization; only the pretrained branch differs. Both runs completed 20000 steps.
Periodic training validation uses up to 64 crops; final comparison must evaluate
the full validation set across multiple conditions. Their final CUDA noise RNG
states and training manifest hashes match exactly. Full-corpus preparation
continues independently.

Local real-camera comparisons confirm RAW support for all four named camera
models. Architecture, ocean spray and sky crops show that RawNIND smooths more
strongly, while our early model retains more grain/texture. These are diagnostic
observations, not proof of a perceptual win. More detail/high-ISO cases and noise
calibration are needed. Private source images and comparison figures remain
local; no personal images have been added to training or published in Git.

## Complete paired 20k-step comparison

The paired suite used all 427 validation photos, 16 separate procedural stress
images, all four Bayer phases, and seven fixed noise/exposure cases. Scores below
are photo means, balanced within each image. Observations and targets are shared
between methods; an eight-pixel border is excluded. Artifacts and exact weight
hashes are in
`/mnt/external/demosaic/evaluation/paired-20k-reference-gains-v2/`.
A compact machine-readable record of the protocol, weight hashes, overall and
per-condition scores is retained in [results/paired-20k-v2.json](results/paired-20k-v2.json).

| Method | Camera-linear PSNR | Rendered PSNR | Rendered SSIM |
| --- | ---: | ---: | ---: |
| DINO, 20000 steps | 35.305 | 29.095 | 0.8527 |
| Matched no-DINO control | 35.274 | 29.041 | 0.8489 |
| Bilinear | 32.332 | 27.555 | 0.8117 |
| Malvar 2004, pre-WB | 34.194 | 28.539 | 0.8395 |
| RawNIND, global CFA gain | 31.217 | 26.671 | 0.7872 |
| RawNIND, per-channel CFA gain | 31.207 | 26.659 | 0.7870 |

DINO's paired gain over its matched control is 0.0534 dB rendered PSNR
(source-bootstrap 95% interval 0.0426–0.0659), 0.0315 dB camera-linear PSNR
(0.0285–0.0343), and 0.00377 SSIM (0.00272–0.00501). This is a modest positive
effect on this synthesis, not evidence of state of the art. Per-channel RawNIND
gain matching does not close its aggregate gap here.

The aggregate hides important failures. Values below average the four CFAs:

| Condition | DINO PSNR / SSIM | RawNIND global gain PSNR / SSIM |
| --- | ---: | ---: |
| ADC only | 29.885 / 0.9144 | 26.265 / 0.7894 |
| ISO 100 prior | 29.843 / 0.9123 | 26.260 / 0.7890 |
| ISO 1600 prior | 29.330 / 0.8821 | 26.192 / 0.7836 |
| ISO 12800 prior | 26.711 / 0.7236 | 25.795 / 0.7594 |
| Shadows | 33.048 / 0.8168 | 33.510 / 0.8524 |
| Highlights | 26.344 / 0.8880 | 22.577 / 0.7590 |
| Earlier noise condition | 28.501 / 0.8313 | 26.097 / 0.7773 |

RawNIND wins shadow PSNR/SSIM and high-noise SSIM. At negligible noise, Malvar
slightly exceeds DINO's PSNR and has higher SSIM. Ours also trails Malvar's
highlight SSIM despite better highlight PSNR. The required broad qualitative
superiority has therefore not been demonstrated. The 387 test sources were not
used. These suites predate the full FP32 physical-color fix below; keep their
archived protocol/source hashes when comparing future results.

## Precision fix and larger noise-conditioned training

An explicit CUDA interpolation check found that BF16 autocast rounded the
original bilinear residual baseline: maximum error was 0.00553 against a float64
reference on the checked sample. New interpolation and physical color transforms
disable autocast and TF32 locally. IEEE FP32 interpolation differed by at most
5.96e-8 on that sample. cuDNN remains enabled. CPU autocast regression checks and
the complete 43-test suite pass. Old 20k-step inference was compared with its
archived source and remains bitwise identical through checkpoint compatibility.

`configs/dino-noise-24576.yaml` starts a fresh 100000-step schedule from the 20k
DINO EMA, using 22059 audited photographic training sources plus 20% procedural
draws. It enables identity-initialized, spatial log-variance modulation at each
restoration scale and IEEE FP32 physical operations. Selection uses the balanced
16-image/28-condition validation panel. The immutable audited split contains
1262 validation and 1254 untouched test sources after excluding one duplicate.
This experiment changes data, precision, conditioning and training budget; any
eventual improvement cannot be attributed to noise modulation alone. Training
results and final quality/speed checks remain pending.

## Broader main-run and smooth-scene comparison

The full paired 427-photo / 16-stress-image suite compared the V4 checkpoint at
16000 steps after DINO20k against V5's 5000-step fine-tuning from V4 step 11000.
They have the same nominal number of restoration updates since DINO20k, but
different LR/optimizer and data recipes; this is not a causal flat-fraction ablation.
Exact hashes and per-condition scores are in
[results/main16k-vs-smooth5k.json](results/main16k-vs-smooth5k.json).

| Method | Camera-linear PSNR | Rendered PSNR | Rendered SSIM |
| --- | ---: | ---: | ---: |
| V4 main, step 16000 | 35.917 | 29.854 | 0.8855 |
| V5 smooth-scene trial, step 5000 | 35.899 | 29.778 | 0.8830 |
| Earlier DINO20k | 35.305 | 29.095 | 0.8527 |
| RawNIND, global CFA gain | 31.217 | 26.671 | 0.7872 |

V4 exceeds RawNIND in mean PSNR and SSIM in each of the seven declared
conditions. In shadows, V4 reaches 34.768 dB/0.8768 versus RawNIND's
33.510/0.8524; at the ISO12800 prior it reaches 28.195/0.8124 versus
25.795/0.7594. These results close earlier synthetic-condition failures, but
real night crops still show substantially more grain than RawNIND. Low-noise
detail also remains a gap: ADC-only V4 scores 29.717/0.9124 versus Malvar's
29.923/0.9294. No global state-of-the-art claim follows from this protocol.

V5's flat-field bias improves, but it trails V4 by 0.0758 dB rendered PSNR
(source-bootstrap 95% interval 0.0717–0.0804 in V4's favor) and 0.00248 SSIM.
It remains stopped at its planned 5000-step review point. V4 was subsequently
interrupted deliberately after verifying a finite, resumable step-30000 checkpoint;
its 100000-step schedule did not complete. Only our own training process was stopped.

## Variance-adaptive residual baseline on the full corpus

`configs/dino-prior-44732.yaml` uses all 40170 training sources from the full
audited corpus (2303 validation / 2255 untouched test / 4 excluded).
Its learned network retains the frozen DINOv3 branch and multiscale noise
modulation, but predicts corrections to white-balanced Malvar interpolation of
a variance-adaptively filtered mosaic. The filter treats each spatial sensor
phase independently, shrinks low-contrast areas toward their local mean, and
returns zero-variance samples exactly. Its local second-moment assumptions are
approximate near clipping and weak texture; neural correction remains necessary.

A 16-photo RGGB pilot found a seven-phase-pixel window better than 15/31 for
noisy photographic detail. The prior is also included as an independent classical
comparator in new quality runs. In V6, V4 step-23000 feature weights initialize
the restoration network; the RGB and mosaic output heads are reset to zero so
its initial output equals the declared prior. Batch size is eight. Ten percent
of clean draws are smooth scenes, 20% detailed procedural and 70% photographic;
independently, 10% of noise draws are ADC-only to train low-noise detail directly.
The first invocation saves/stops at 5000 steps before continuing the 100k schedule.
These changes are a new recipe, not an isolated architecture ablation.

At V6 step 1000, the 16-photo balanced monitor is 31.0246 dB/0.91337 SSIM.
RGGB ADC-only reaches 31.352/0.9447 and shadows 36.163/0.9083. At step 5000,
the balanced monitor reaches 31.3982/0.91846. These are training-monitor scores;
full-set evaluation and final qualitative checks remain pending. On a 0.01-level
ISO1600-prior flat, residual sigma falls to 0.260 of bilinear versus V5's 0.632;
RawNIND still reaches 0.0356. Real night crops visibly reduce the older model's
grain, but low-frequency color variation remains. Passing software tests alone
does not establish final restoration quality.

The V6 step-1000 model processed an entire 8746×11662 GFX100S RAW to linear
camera RGB16 and ICC-tagged sRGB16 TIFFs. TIFF tags, dimensions and many
non-8-bit-grid values were checked. With two concurrent training jobs, cold
restoration took 39.264 s and decode/load/restore/preview/encode took 58.714 s;
this is a capability check, not an idle speed benchmark. Peak allocated CUDA
memory was 0.820 GB; host RAW/output arrays are additional shared-DRAM allocations.
The idle, warmed step-5000 100 MP benchmark takes 12.767 s, excluding decode,
checkpoint loading and encoding. Compiler acceleration is being evaluated
separately with explicit numerical comparisons.
