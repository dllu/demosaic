# Multiscale measured-CFA correction trials

Previous turn made progress: new GFX pair/crops, optional FP16 refinement and
completed native body/control review committed/pushed. The full goal remains
open: V16 still trails RawNIND on real development and misses 10 s per 100 MP.

Implemented an optional 255,840-parameter pyramid correction with noise-unit
RGB, variance/CFA/context features and direct packed RAW minus CFA-sampled
prediction innovation. Its two-level gated encoder/decoder starts as identity;
zero sensor variance forces zero correction. Existing checkpoints disable the
new branch. Physical operations remain IEEE FP32. Added mutually exclusive
pyramid-only training and exact resume mode checking.

All 182 tests passed in 12.44 s; Ruff passed. Tests verify measured-CFA access
across four patterns and its removal in the control, arbitrary even geometry,
warm start, frozen weights, zero variance, CUDA half/FP32 physical outputs and
exact CPU resume. Genuine DINO/V16 startup checks covered 6,291,456 RGB values
per arm: both are bitwise identical to the parent across four CFAs and ADC/noisy
conditions. Initial restoration weights match between arms.

Started V24 control (innovation zeroed) and V25 (innovation enabled), with the
same 255,840 parameters, seed 45, LR 5e-4, original 50/50 paired/Commons losses
and data, per-step RNG, and sampled batch hashes. Planned 5000-step schedule;
stop at the first 1000 steps for review. Existing body/DINO/fine branch frozen.
No native-target substitution or protected final/GFX scenes. Startup sampled
hashes match. Own jobs: sessions 6699/71267, logs
`.cache/train-pyramid-{control-v24,raw-v25}-1k.log`; source archived per run.
Observed step 50: finite gradients/loss, about 0.5 s per step per arm under
concurrency, about 1.81 GB peak CUDA each, and 70 GiB system memory available.
Do not restart on observation timeout.

Hypothesis: direct measurement access and larger context may restore detail
removed by preceding stages and suppress coarse residuals. Startup checks do
not prove that. No promotion or performance claim. Review both real panels,
the matched synthetic screen, and at least two native triplets per candidate.
See `docs/pyramid-refinement.md`. The inspected AIM 2025 abstract is context
for camera-general synthetic training, not a reproduced method or evidence
for this untested innovation representation.
