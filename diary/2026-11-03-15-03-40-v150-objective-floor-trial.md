# V150 matched loss-floor trial

Recorded: 2026-11-03T15:03:40-08:00 (America/Los_Angeles).

Started a matched2/16 DN loss-floor trial after the completed supervision
allocation probes showed large ADC pressure. Both heads retain the identical
31,409-parameter native matrix architecture and twelve initial tensors. Only
the per-image RGB standard-deviation floor and per-phase spectral variance floor
change together. Existing source/geometry/domain weights, pre-gate spectral
objective, physical inputs,1k horizon, LR/schedule/clipping and EMA remain fixed.
Adopt all1,000 V148 batches/4,000 old observations and parents, with no new
training noise or parent/DINO call. No neural or inference source changed.

Added8 old exact synthetic photographic ADC observations (bark/fur across4CFAs)
and16 new analytic native512 sloped-plane ADC observations, all held out from
training. Both photographic source IDs retain the original train-disjointness
audit, matching train manifests and absence from actual cached training metadata.
Two older approximate binned camera references were deliberately not adopted.
Independent long-double checks cover4,194,304 new packed ADC values, maximum
FP32 difference .001953 DN16. Direct quantization draws no stochastic noise.

Cached24 new V143/DINO parent contexts before head training. All24 calls finish
with model/backbone hashes and CPU/CUDA RNG unchanged, peak .99 GiB CUDA. Only
cached repo/external inputs are read; originals/protected siblings remain read
only and excluded, with no RAW/dataz access. These controls are never fed to
training. All4 final raw/EMA endpoints cover822 cases and3,288 component calls.
The72 fixed native figures include24 repeated triplets and both standing real
scenes, mesh priors/windows/JPEGs. Real ISO100/AHD/JPEG references remain
qualitative, not exactGT; actual blank/DC/spatial and quiet errors remain in review.

All8 new objective tests passed in1.10s over4CFAs and ADC/high-noise cases.
Helper2 DN exactly matches the old coefficient value/gradient;16 DN leaves the
high-noise value/gradient unchanged and scales ADC spectral gradient by1/64.
Compatibility preserves28 trained old/current/archive cases exactly (56 actual
forward-function evaluations). Both fresh heads pass CUDA10 each with genuine
8+2 restoration, all12 nonzero finite gradients and4.07 GiB peak. Production
starts fresh afterward, with no worker replacement/restart.

The reporting preflight passes64 parent cases (32 mixed+8 meshes+24 ADC),280
independent scalar checks, maximum1.24e-13 and no CUDA initialization/NN/noise
calls. Its first harness used the original review-module name instead of the
frozen file path and stopped during imports. Preserve that source/error and
load the actual frozen review file; no reporter/model/input/worker changes.

Checkpoint250 contains24 finite Adam states and finite raw/EMA weights in both
heads. The native control's raw/EMA/Adam state matches V149 exactly. Preparation
publication records an active423-row complete native loss/gradient/LR trace
prefix, exact against V149, with both controllers and the training worker
verified live. All13 receipt copies preserve their original bytes. This is
readiness and active-state evidence, not quality improvement. The final1k
states, every fixed endpoint, independent scores and actual native viewing are
still pending. The broader fine-detail/clean-sky goal remains active and unmet.

[Protocol/current status](../docs/objective-floor-training.md) ·
[Preparation evidence](../docs/results/v150-objective-floor-preparation-v1.json).

