# Head-only training engineering checks

The opt-in [V92 training-scope experiment](late-rgb-head-only-v92.md) freezes
the genuine V63 common path while learning the existing global late RGB head.
This document records execution/state checks, not a quality or speed result.
Architecture and inference defaults remain unchanged; no model is promoted.

`late_rgb_only: true` makes only the24 head tensors /100,547 parameters
trainable. The1× optimizer group is empty and the20× group contains all24;
AdamW creates only24 states. All91 common restoration tensors and the frozen
DINO remain at V63. Scoped EMA updates only head parameters. Measurement and
common decoder/conditioning/DINO inputs require no gradients, so no common
backward graph is built. Gradient clipping consequently covers the head alone.

The option must be a boolean, requires a real late head and rejects concurrent
head-only modes. Resume rejects a changed scope before backbone construction.
Legacy configurations retain complete-state EMA and trainable-parameter
selection. The original `lerp_` already preserves equal frozen values; this
change explicitly limits EMA scope, without claiming a former rounding bug.

All34 expanded late RGB tests pass in92.46s, including global/spatial heads,
FP32/BF16 CPU forwards, absent common backward inputs/gradients, one encoder
call per actual forward, exact common model/EMA, valid head learning and actual
four-update interrupted training. The78 training/execution/RAW/component
regression tests pass in15.81s. Ruff passes. An initial regression collection
omitted `scripts` from `PYTHONPATH` and ran no tests; its failed JUnit remains
preserved separately from the corrected passing command.

## Genuine CPU16 and fresh-process8+8

The [frozen CPU plan](results/late-rgb-head-only-CPU-plan-v1.json) uses actual
V63 original20k/DINO weights and the reviewed prepared mixed-domain data,
B1/native64/FP32, retaining seed55 and the original4000 LR horizon. Three
separate workers run16,8 and8→16 updates. No quality checkpoint is selected.

The [completed controller certificate](results/late-rgb-head-only-CPU-preflight-v1.json)
requires exact uninterrupted versus resumed model, EMA, AdamW, best, step,
model configuration and Python/CPU/CUDA RNG. All16 source/forward/loss
fingerprints, domains, scheduled LRs and final RNG match the original global
V90 CPU preflight. Every boundary retains finite115 model/115 EMA/24 AdamW
states; each AdamW counter equals its actual step. Learned head output and
modulation weights are nonzero. Common gradients are absent and all91 common
model/EMA tensors remain exactly V63. DINO remains frozen and unchanged.

The independent [CPU byte audit](results/late-rgb-head-only-CPU-byte-audit-v1.json)
compares canonical tensor bytes, including signed zeros, at all three saved
boundaries. It separately checks all final model/EMA/optimizer/RNG fields
across the real process restart, without initializing CUDA or rerunning a
network forward. The initial complete model hash matches the original V90
state, `71104eb4dcf64d56f8acbfabd770905672a422a5acb6e43f8ca1de217603e437`.
The actual frozen DINO hash remains
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.

## Genuine CUDA16 and fresh-process8+8

The [frozen CUDA plan](results/late-rgb-head-only-CUDA-plan-v1.json) uses the
actual B16/native256/BF16/channels-last production recipe. Its
[completed certificate](results/late-rgb-head-only-CUDA-preflight-v1.json)
passes the same uninterrupted16 versus genuinely separate8+8 checks: all
model/EMA/AdamW/RNG/best states, every logged observation, original V90 inputs
and LRs, initial model/DINO state and absent common backward. All91 common
model/EMA tensors remain V63 at each boundary, with only24 finite AdamW states.

The independent [combined CPU/CUDA byte audit](results/late-rgb-head-only-CPU-CUDA-byte-audit-v1.json)
checks all six saved boundaries and both actual process restarts on CPU,
including tensor bytes and signed zeros, without initializing CUDA or running
another network forward. Only `train.py` differs across all47 executed model
modules relative to actual V90; every inference module is byte-identical.
The [engineering index](results/late-rgb-head-only-engineering-v1.json) binds
both certificates, the independent audit, all112 passing tests and executed
module hashes before launch. These discarded updates are not throughput or
quality measurements.

## Original4000 run and remaining review

The [full frozen plan](results/late-rgb-head-only-full-plan-v1.json) launches
one fresh V92 candidate from V63, retaining the original4000 schedule and
64,000 examples. Both preflight controllers/workers have exited. Full controller
1265645/create1792504985.8 launches owned worker1265932/create1792505056.08
after60s of resource headroom, with the protocol's RAM/disk/CUDA/runtime limits and no automatic retry,
extension or promotion. Its external operational status is
`/mnt/external/demosaic/experiments/late-rgb-head-only-v92-original4k-v1/status.json`.
The [observed startup receipt](results/late-rgb-head-only-startup-v1.json)
verifies both exact live owners, actual first-forward parent parity and the
first16 source/forward/loss fingerprints against original V90.
The independent [first1000 state audit](results/late-rgb-head-only-first1k-state-v1.json)
now confirms all91 common model/EMA tensors still match V63 byte-for-byte,
finite115/115/24 states and all56 logged observations through1000 matching V90.
This is a retained engineering milestone, not early quality selection.
The [full quality/native queue](late-rgb-head-only-review-preparation.md) is
source-frozen and verified waiting for exact successful training exit.

Original4000 completion, full FP32 quality evaluation and actual native/GFX
viewing remain separate requirements. The completed V90 is a fixed historical
exploratory reference, not a freshly randomized control. Engineering success
does not establish improved photos, SOTA, decisive real-photo superiority or
100MP/10s. Working V43 and representative README crops remain unchanged.
