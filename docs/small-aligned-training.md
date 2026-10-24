# Small quality training from the current baseline

**The next Small initializer is being rebased onto V112.** V112 now combines
higher camera means and much lower ADC color bias with V111-like photo PSNR.
The earlier V104-derived V113 queue was stopped while still idle, before any
CUDA or production updates. [Current baseline](v112-quality.md) ·
[Actual supersession boundary](results/small-aligned-v113-superseded-v1.json).

## Current next step

Reuse the retained Small training features and cached previews from the
[existing transfer fit](small-feature-transfer.md). Compute new Tiny teacher
lateral targets from V112, preserving its learned gates and restoration trunk.
Keep fitting and feature-check sources separate and keep validation, test and
GFX captures outside fitting. Verify preview normalization before reusing
features; changing the teacher does not justify repeating the Small encoder
or source augmentation unnecessarily.

Then verify the new serialized initializer and actual optimizer behavior,
perform native256/B16/BF16 CUDA checks when the original GPU chain releases
CUDA, and freeze a new explicit training plan from the successful initializer.
Use V112's cleaned90,864-source, zero-PSF, weak-detail/contrast recipe and trained
loss scale. The new fit, GPU check and production run are not yet claimed complete.
Quality comparisons must retain source budgets, native triplets, camera/color
and standing GFX evidence, with accurate reference labels.

## Preserved implementation evidence

The earlier V104-derived fit changes eight lateral tensors and keeps83 EMA
tensors and all three nonzero learned gates exact. It uses64 training sources
for fitting and16 different training sources for feature checking. Its inherited
step20000 records V104 history and zero new joint updates.

Eight actual discarded CPU64/B1/FP32 forward/backward/AdamW/EMA updates pass.
All91 initial EMA tensors match the fitted checkpoint; all89 fresh Adam states
reach step8, with finite model/EMA/Adam and no gradients in the frozen official
Small encoder. Every actual input/domain/step/LR matches V111's earlier CPU
check. [Original source, recipe and CPU evidence](results/small-aligned-training-queued-v1.json).
These are implementation results, not trained Small quality or timing results.

The original V113 recipe, prospective sources, controller log/terminal status
and CPU checkpoint remain preserved. Only its verified waiting controller was
stopped; original GPU evaluation/export/dihedral/audit owners were untouched.
The recorded terminal KeyboardInterrupt is an intentional planning change,
not a numerical failure or automatic retry. The older zero-gate capacity
preparations also remain preserved and unlaunched.
