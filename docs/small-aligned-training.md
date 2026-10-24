# Matched quality training from V112

**V114 Tiny has started its original 20,000-update continuation; V115 fitted
Small follows with the same budget.** Both passed eight actual native 256/B16/BF16
CUDA updates after the original eight-view evaluation/audit exited successfully.
They use seed 63 and V112's trained loss scale. V112 remains the current learned
baseline while endpoint quality is unmeasured.

[Plans, actual CPU checks and queue boundary](results/v112-continuations-queued-v1.json) ·
[V112 baseline](v112-quality.md) · [Completed Small transfer](small-feature-transfer.md).
[Guarded training launch and successful CUDA checks](results/v112-spawn-guard-training-and-evaluation-v2.json) ·
[Current corrected evaluation/review queues](results/evaluation-backbone-interface-fix-v1.json).

## Models and budget

| Arm | Initialization | New production updates |
| --- | --- | ---: |
| V114 Tiny | All 91 V112 EMA tensors and official frozen Tiny encoder | 20,000 |
| V115 Small | V112 trunk/gates with fixed 64-source lateral fit and official frozen Small encoder | 20,000 |

Small changes eight lateral tensors; the other 83 EMA tensors and all three
learned fusion gates remain exact to V112. Its initializer records inherited
step 20000 and zero new joint updates. Sixteen separate training sources check
the feature fit; validation, test and GFX do not enter fitting.

Both use the same cleaned 90,864-source corpus, reviewed low-contrast ROIs, zero
optical PSFs, photographic contrast and weak-detail recipe. Training uses
native 256/B16/BF16, LR 1e-5 with 200 warmup updates, Charbonnier epsilon .0003,
fresh AdamW/EMA and deterministic per-step data seeding. Seed 63 supplies new
draws relative to V112's seed 62 continuation. Total new production budget is
40,000 updates. Completed V112 is a reference; V114 supplies the matched
extra-training control for V115.

[V114 recipe](../configs/quality-v112-tiny-continuation-v114.yaml) ·
[V115 recipe](../configs/quality-v112-small-aligned-v115.yaml).
This compares the fitted larger-encoder transfer method with an equal-budget
Tiny continuation. The feature fit is an additional intervention.

## Completed implementation checks

Each arm passed eight actual CPU 64/B1/FP32 forward/backward/AdamW/EMA updates.
All 91 initial EMA tensors match its explicit parent, all 89 fresh Adam states
reach step 8, and model/EMA/Adam remain finite. Both official encoders stay frozen
with no gradients. All eight actual input hashes, domains, steps and learning
rates match between arms. Those steps cover paired, native and Commons data.
Source archives are identical. These sixteen updates are discarded; the
controller adopts their receipts without repeating them.

Execution order is CUDA check V114, CUDA check V115, production V114, then V115.
Both CUDA checks are eight discarded updates at native 256/B16/BF16. Production
starts fresh from its explicit initializer; its first output/loss must match
its own successful CUDA check. The worker checks optimizer/forward counts,
frozen encoder identity, finite state and the recorded input schedule. Small's
logged inputs/domains/LRs must match Tiny's eight CUDA rows and 801 production
rows. Unlogged production inputs are not independently verified.

## Queue and quality review

The queue binds the original audit owner's PID/creation time, plan and successful
terminal receipt. Earlier owned GPU processes must exit. It observes 48GiB
available RAM, a 24GiB model memory quota, 248GiB free external space before each
new phase and a 240GiB runtime reserve. These are prospective limits; the earlier
workflow's frozen reserve remains unchanged. Failures preserve attempted work,
sources and logs and stop without automatic retry.

Endpoint evaluation must compare V112, matched Tiny and fitted Small on complete
photo/camera/analytic panels. Publish at least two native noisy / denoised /
exact synthetic GT triplets plus standing GFX foliage/fence and other regions
with accurate reference labels. Document useful progress and weaknesses directly,
without a study-specific significance gate freezing implementation or examples.
Quality precedes speed.

The [old V104-derived CPU check and V113 plan](results/small-aligned-training-queued-v1.json)
and [intentional idle supersession](results/small-aligned-v113-superseded-v1.json)
remain preserved. They have no production CUDA updates and are not resumed.

The [retained-prediction endpoint evaluation](quality-prediction-archive.md) is
now queued behind this exact training controller. It covers the complete
photo/camera/analytic panels, six GFX contexts and complete 102MP exports for
both new models, reusing existing V112/RawNIND controls. Exact numerical targets
and native FP32 predictions will be retained for independent review without
repeating model inference. Its controller is waiting with no child or CUDA work.
An independent CPU audit is also queued after that exact evaluator. It checks
the retained numerical panels, source/scene comparisons and color/detail tails,
and prepares native bark/canopy triplets. Actual photo/GFX viewing follows.

The first CUDA wrapper lacked a multiprocessing main guard. A spawned loader
re-entered it and failed before the first batch; the root receipt confirms zero
prepared batches, forwards or optimizer steps. The original controller stopped
the attempt and its dependent evaluator stopped without CUDA. Sources, logs,
receipts and partial directories remain preserved. A corrected wrapper passed a
real spawn-import test, then both actual eight-update CUDA checks with identical
inputs/domains/LRs and finite state. The original 16 CPU updates were reused.
