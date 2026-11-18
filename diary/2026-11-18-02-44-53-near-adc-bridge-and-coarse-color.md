# Matched noise-range continuation and intermediate color repair

Recorded: 2026-11-18T02:44:53-08:00 (America/Los_Angeles).


The measured gap in training is the target of a matched pair of
800-update, native256/B16 continuations. Both start with the actual
100k EMA and fresh AdamW. The bridge arm re-simulates half the
ADC-only examples in the two synthetic domains with 4–160 codes RMS
at full signal and 0.7–1,500 read electrons. Source indices, camera
transforms, clean targets, paired samples and all previously positive
noise profiles stay matched. The shared source plan includes 4,325
ordinary-photo visits from the 90,778 eligible images.

CPU preflight uses the first 512 actual training data slots. It
regenerates all 23 changed RAW observations exactly, with the original
targets and every unselected value preserved. One initial unit fixture
selected zero samples. A replacement fixture selected a fully saturated
native crop, so the added noise could not alter its displayed ADC codes.
The final fixture verifies the intended unsaturated-sample effect.
The integrated suite passes 182 tests.

The 86k EMA has finite loss and 89 finite gradient tensors on the
lowest-noise and highest-read-noise samples in the actual CPU
preflight. The first standalone backward attempt omitted the
trainer's default gradient epsilon. The rerun uses the same
default resolver as training. Neither attempt updates the model.

The intermediate-noise color correction is a separate opt-in helper.
It repairs the 86k reserved magenta tail from 6,702.67 to 809.64
DN16 mean error. It reduces the prior bright-yellow tail from
7,879.99 to 596.02 DN16. All 128 matched V120 and 86k photograph
predictions and all 18 standing camera predictions return by object
identity. Two flat triplets and two photo comparisons were viewed.
The measured weak-detail on those photos stays at the earlier level.

At publication the continuations and their independent native and
near-ADC evaluations are waiting for the 100k checkpoint. A separate
observer is bound to audit the original run's full source and
conditioning traces after completion. The canonical PSNR record
has no new endpoint from these prepared jobs.

[Matched continuation](../docs/near-adc-bridge-training.md) ·
[Intermediate color repair](../docs/coarse-adc-color.md) ·
[Standing main GFX](../docs/gfx-qualitative.md) ·
[Standing cab GFX](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
