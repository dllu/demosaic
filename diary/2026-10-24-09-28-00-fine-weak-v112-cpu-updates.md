# Check fine weak textures in actual V112 optimizer updates

Recorded: 2026-10-24T09:28:00-07:00 (America/Los_Angeles).

Previous goal turn was progress: `9fc4e32` measures clean-target spectral
coverage and adds the optional fine-v1 profile without changing current
recipes. This turn revalidated training 867877/1792848017.25 and both exact
waiting reviewers before new work. Broad real-photo superiority and faint
fine-detail recovery remain unmet.

The prior eight V112 CPU64/B1 updates have no weak source draw, so merely
enabling fine.075 there would not exercise it. Metadata-only inspection of the
original seed63/B16 schedule identifies five fine replacements in its first
eight updates: indices37/39 fibers and45/117/120 random fields, at steps3/8.
This fixes the engineering coverage before new learned execution. Existing
CPU B1 or CUDA256 results cannot supply the new CPU64/B16 matched control.

Froze a legacy/fine comparison from exact V112, actual90864-source/six-ROI
inputs and current library sources. Only fine_weak_texture_fraction0→.075 and
output paths differ. Both retain weak.15, seed63, zero PSFs, epsilon.0003,
original LR/warmup and planned20000 cosine horizon, with fresh AdamW/EMA and
stop_after8. Native64/B16/FP32, two threads and zero loader workers keep the
engineering check CPU-only. It is not a new production budget or quality model.

The first source copy omitted required third-party license artifacts. The
trainer stopped before model construction, root/encoder forwards or optimizer
steps; all three counters are0. Preserved that source, plan, log, zero-work
receipt and partial directory in fine-weak-training-CPU-v1. Corrected v2 adds
the exact three license files, new run/evaluation paths and failure bindings;
all model/data/loss/noise source bytes and the worker itself remain identical.
No successful learned work was repeated. The first attempt's fine arm never ran.

Both corrected arms complete eight actual real-model forward/backward/AdamW/
EMA updates each. Total16 root and16 encoder calls,16 updates,256 sample draws:
per arm64 paired,16 native synthetic and48 Commons. Actual new synthetic noise
observations total128; paired observations are registered captures. All91
initial restoration EMA tensors match V112; all89 Adam states reach8. Model/
EMA/Adam remain finite and the official frozen Tiny hash remains exact, without
gradients. All clipped gradient norms are finite and positive. No validation,
new GPU call, standing-GFX decode or current-model change occurs.

Retained all actual clean Commons arrays, all eight physical training batches
and root outputs per arm, both checkpoints, metrics and generator recipes.
All110 source cache arrays read in each arm have identical paths/order/bytes.
The actual fine arm has exactly five fine targets, covering both generator
modes. The other43 Commons targets remain bit exact. All nine weak draws
retain seed, kind, background, tint, peak contrast and post-generator geometry
RNG states. The first two root outputs and losses are bit exact, before the
first replacement batch. Domain and LR schedules match for all eight updates.

Independent NumPy array rereading imports no Torch and adds no model call,
noise draw or update. All camera/WB/CFA/shot/read parameters are bit exact.
Six complete physical batches match; clean/sensor targets change only in the
five intended slots. At step3, Poisson RNG consumption changes noisy/variance
slots0/1/2/4–15, although target changes are only5/7/13. At step8, noisy/variance
slots5/6/8 change, with target changes only5/8. Therefore this is not a claim
that every unchanged-target sibling has identical noise. Per-step RNG isolates
later unchanged batches. The per-field differences are retained explicitly.

The actual CPU check proves current-model training-path compatibility and
coverage, not learned quality, convergence, native256/BF16 CUDA validation or
speed. Both smoke checkpoints stay separate from selected models. A later
matched trained-quality experiment must use the useful architectural baseline
after current V114/V115 results and preserve flat/color/photo/camera/GFX review.
No new production recipe or GPU job is scheduled by this check. Existing28
targeted tests are not repeated for documentation; current source bytes match
the tested implementation.

[Current coverage and real-model check](../docs/fine-weak-texture-coverage.md) ·
[Actual updates and independent audit receipt](../docs/results/fine-weak-real-V112-CPU-v1.json).
Private frozen evidence is under .cache/current-quality-20261023-v1/
fine-weak-training-CPU-v1/ and fine-weak-training-CPU-v2/.

Final verification at 2026-10-24T09:32:04.308960-07:00: five frozen plan guards,
464 bound files and 197 local links pass. Both CPU owners exited; current
library sources match their executed snapshot exactly. V112 selector and
checkpoint hash remain verified. Original training owner867877/1792848017.25 is
live at logged V114 step13100; evaluator986158/1792855221.87 and independent
audit986159/1792855223.35 remain live/waiting, with no children or completed
stages. Internal output leaves external free space at255.21GiB; available RAM
is77.8GiB. No broad performance or model-quality completion claim follows.
