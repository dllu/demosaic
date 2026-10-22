# Spectral residual engineering checks and fixed training launch

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

The optional measured-RAW Fourier residual passes68 targeted tests and genuine
CPU/CUDA16-update mixed-domain preflights. Its68 new parameters initialize at
zero, preserving parent predictions and common gradients. **These are discarded
engineering checkpoints, without a restoration-quality or speed result.**
The [fixed V88/V89 protocol](spectral-v88-v89.md) defines the next comparison;
V43 was the reference for this experiment.

An identified final double-save bug in this experiment's retention wrapper has
an [explicit verified1000-checkpoint recovery](spectral-retention-recovery.md).
The corrected CPU/CUDA and external-resume checks pass, and production has
resumed its original4000 horizon. All46 model modules, data and losses stay fixed.
The [subsequent resource recovery](spectral-resource-recovery.md) records the
64GiB root-reserve addendum and current active root. Full final evaluation and
native packaging are [validated and queued](spectral-review-preparation.md).

[Complete preflight/hash/state receipt](results/spectral-engineering-preflights-v1.json).
[Launch observation](results/spectral-original4k-launch-v1.json).

The independent dense complex float64 DFT agrees with FP32 Fourier spectra,
shared phase masks and signed measured-site innovations on odd/even rectangular
inputs. Tests cover every CFA and native rotation/reflection, separate batches,
WB units, zero-DC/constant/ADC arithmetic, complex backward against finite
differences, default-off configuration, complete parent values/common gradients/
RNG, head learning-rate groups and nonzero-head checkpoint reload.

Both preflights use genuine original V63 step20000 EMA and official frozen
DINOv3 ConvNeXt-Tiny. CPU uses B1/native64/FP32; CUDA uses the intended
B16/native256/BF16/channels-last. Each device runs16 control updates,16 spectral
updates and an8+8 restart of the spectral arm, with the original4000 LR horizon.
Their five Commons, six native and five paired steps have identical saved source,
actual-forward and actual-loss hashes between arms. The new head learns and
DINO remains unchanged. Within each device, uninterrupted and resumed model,
EMA, AdamW, counters, best bookkeeping and Python/CPU/CUDA RNG are exactly equal.
This does not claim CPU/CUDA numerical equivalence or training convergence.

| Arm | Model/EMA tensors | AdamW states | CUDA peak allocation, decimalGB |
| --- | --- | --- | --- |
| Control | 91/91 | 89 | 6.93941 |
| Spectral | 93/93 | 91 | 7.24191 |

All states are finite; AdamW counters equal16 and second moments are nonnegative.
All exact preflight owners have exited. A separate CPU collector verifies frozen
files/inputs, retained checkpoint bytes, state/RNG equality and saved observation
records. It does not regenerate neural outputs or every source batch. Allocation
peaks from16 updates are not a throughput sweep or full-frame memory result.

## Production comparison

The separately frozen original4000 trial uses285 archived files,46 actual model
modules and780 input bindings, plan SHA256
`1263ce0f2673afd4e3ebacab9ef8c3bb368934bd19d4553f50ca7676873ac9f2`.
Its controller runs one arm at a time after stable resource checks, using all
88,508 reviewed future Commons sources plus the unchanged native128/paired32.
Both arms keep native256 and the4×→geometry/PSF→area2 path. The new Fourier
head and its20×head LR are the intervention; common data, losses and base LR
remain fixed. The larger-context result does not support discarding smaller
sources for another320px training field.

The initial run is preserved under
`/mnt/external/demosaic/experiments/spectral-v88-v89-original4k-v1/`.
The launch observation verifies the exact live controller/worker through logged
control update100, all three source domains and20 recorded matching
source/actual-forward/actual-loss observations. It is a captured startup record,
not a terminal result or a replay of unrecorded samples.
The current active run is under
`/mnt/external/demosaic/experiments/spectral-v88-v89-resource-recovery-v2/`;
the resource recovery report records state checks and current owners.
Only final original4000 endpoints are eligible for the declared full photographic,
real-camera, analytic, hue/highlight and actual native-crop review. There is no
automatic continuation, default change or promotion. GFX3879/3880 and siblings
remain qualitative-only, with ISO100 accurately labeled as an independent
different-aperture/time reference. SOTA, broad superiority and100MP/10s remain
unmet or unproven.
