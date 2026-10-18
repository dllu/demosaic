# Test candidate-bank context with fixed fresh training

The previous turn made concrete progress: explicit training execution, repeated
strict state identity, measured execution cost, and a separately admitted private
native dataset. Quality, broad real superiority and the 100MP/10s target remain
unmet/unproven. This turn addresses the weak-detail limitation with an isolated
architecture experiment.

The existing directional head computes long-range RAW averages but its mixing
network receives local innovations and mature RGB/DINO features. Added optional
`raw_directional_bank_context`: a small packed network processes all five
candidate-minus-parent residuals, scaled by the original measured noise. Its
zero output head corrects the existing mixture logits. It reuses each average,
adds 24,543 parameters in six tensors, preserves common RNG/parent prediction,
and never receives targets/frequencies in forward. The censored head is unchanged.
Old checkpoint defaults and disabled training reproduce prior strict states exactly.

32 focused tests pass, including nonzero-parent output/common-gradient identity,
FP32/BF16 checkpoint roundtrip, long-range evidence outside the local window,
constant-scene behavior and learning after the zero head opens. The final CPU
suite passes 1,130 tests with 9 skips in 111.10s. Ruff/format/diff checks pass.

Actual genuine V63/DINO CPU mixed training completes control/bank four updates,
plus exact bank2+2 resume. The disabled control equals the prior strict CPU
checkpoint in all logical fields (normalizing the new default config flag).
All initial 97 common raw gradients match. All 105 model / 105 EMA / 103 AdamW
states and gradients are finite for the enabled model; control retains 99/99/97.
A harness assertion initially included randomized bank hidden layers among zero
heads and stopped before the first bank update. Its source/plan/failure receipt
are preserved; the corrected CPUv2 run passes.

Actual CUDA B16/native256/BF16 six-update control/bank checks pass across
Commons/native/paired. Both select identical inputs and share exact initial
common raw gradients; the disabled control equals the earlier strict GPU state.
DINO is unchanged/frozen. Peak allocation is 7.3963/7.6471 GiB. These are discarded
engineering checks with startup/validation, not throughput or quality results.
Global clipping includes new head gradients; clipped common gradients may differ.

Predeclared docs/directional-bank-v80-v81.md and two configurations fix fresh
V63 EMA initialization, strict execution, seed51/B16, original complete4k cosine
horizon, warmup100, LR1e-5/branch20x, interval0 and sensor-valid supervision.
Both use cleaned Commons84867/native128/paired32 with existing geometry and
selected-domain loading. The private150 addition stays inactive. Old studies and
failed gates remain closed. Two 64k-example budgets are serial and not convergence.

The first controller launch omitted sibling scripts from its safe-path import
search and would fail its final audit import. Stopped only the exact owned
controller/worker groups after25 logged control updates, with no saved boundary
checkpoint or quality review. Removed that late sibling dependency and explicitly
provided frozen module paths. The isolated v2 has a fresh232-file freeze and
fresh optimizer/RNG, unchanged data/criteria and both full4k budgets.

The active controller and worker PID/creation identities are recorded in the
v2 status file. Always recheck actual identity before use; static prose is not
liveness evidence.
Root .cache/experiments/directional-bank-v80-v81-original4k-v2. The worker retains
1k/2k/3k states, samples176 observations/161 logged domains/LRs and verifies final
RNG. Caps24GiB CUDA/40GiB launch RAM/128GiB root/500GiB external and 10800s/arm.
First active control loss equals the strict replay. No other jobs terminated.

Review requirements retain camera/photo eligibility, canonical target caveats,
full427/known4/unseen5/color/analytic/source sensitivity and real/native crops.
A bank benefit also requires each fixed weak carrier's signed gain to improve
at least .05 and corresponding flat RMS no more than1.25x control. No thresholds
were changed after trained quality results; none exist yet. At least two native
100% noisy/restored/exactGT triplets per improved-model report and cached GFX
foliage/fence/sky/building/lights remain mandatory. Independent real references
stay labeled accurately. No full-frame export, protected-final score or promotion.

The training is live, and final reviewer preparation/queue and actual quality
closure remain outstanding. See docs/directional-bank-engineering.md and its
launch registry. All originals stay read-only; standing scene/siblings excluded,
source HDDs untouched, downloader off at its free-space reserve. Goal stays active.
