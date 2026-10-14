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

The final row includes validation/host accumulation/normalization and avoids a
second full-image Bayer packing allocation. GPU kernels were warmed. It excludes
RAW decode, checkpoint loading and TIFF encoding. Timing includes process noise;
repeat idle measurements and the final trained network are still needed. See
`/mnt/external/demosaic/benchmarks/` for machine-readable records.

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
This run uses the initial camera-space highlight mask and ADC black=0.

`highlight-v3` adds a rendered-space highlight mask and an ADC black offset so
negative black-subtracted read noise survives. New runs archive the actual source
code/lockfile and manifest SHA. These changes need trained-model validation and
comparison with v2. The v3 config is available; its training is not yet established
by this document.
