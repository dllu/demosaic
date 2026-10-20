# Preserve the resumed control's additional training log

The resumed V88 control logs its first new update, **1,001**, in addition to
the regular first/every-25-step logs. Its original frozen wrapper expects only
161 regular rows and would reject the 162 real rows after completing all 4,000
updates and saving the final checkpoint. This is a completion-checker error.

`scripts/complete_spectral_logging.py` adds an explicit coordinator without
interrupting, restarting or extending the current control. It waits for the
original exact controller/worker exits. It accepts only the known post-training
assertion, independently checks the saved 4,000-step model/EMA/AdamW states,
original terminal LR and identical retained final checkpoint, and preserves all
162 metric rows and all 176 forward/supervision observations. The source and
traceback place the frozen-DINO and finite-state checks before that assertion;
this does not claim a new direct measurement of the exited worker's DINO memory.

The spectral arm then uses the unchanged frozen worker, original model package,
data, conditioning, seed and original 4,000-update schedule. Compare the 161
shared scheduled log rows between arms; retain the additional control row in
the evidence. Match all 176 recorded observation dictionaries, source archives
and final RNG states. No quality threshold changes or automatic promotion occur.

Current coordinator plan:
`/mnt/external/demosaic/experiments/spectral-v88-v89-log-completion-v1/plan.json`,
SHA-256 `e595dfb8808cb33b0d147047e4a33519ee612c5281061275356d16f6c6d59cf4`.
The original training work/run/config paths stay in
`spectral-v88-v89-resource-recovery-v2`. The new directory contains completion
metadata and the fresh arm's wrapper outputs. The earlier idle evaluation and
inverse-probe followers were explicitly cancelled for queue rebinding; the
cancellation receipt identifies all five exact owners and confirms the active
training owners were untouched.

The [intermediate integrity audit](results/spectral-replay-and-step2000-v1.json)
checks the genuine saved step-2,000 state and the entire recorded discarded
segment: **30/30 observation dictionaries and 31/31 loss/gradient/LR logs replay
exactly**, including 1,001. This is trajectory integrity, not a quality result.

The review adapter now accepts exactly the declared additional resume row and
rejects missing, unexpected or duplicate rows. Its focused CPU suite has
**42 passing tests**. CPU integration replays the existing real 16-update
engineering states and historical criteria/native packaging before the new
production queue is allowed to launch. Full quality inference and actual native
crop inspection remain required after both original budgets finish.

The rebound full review is
`/mnt/external/demosaic/experiments/spectral-v88-v89-final-log-review-v2/plan.json`,
SHA-256 `753f0fca62747cf3dd4646d31e81fd33942f40dad82c00388c31059d345e84a0`.
Its review/closure/reference and native-package watchers are live and waiting.
The fresh CPU integration receipt is
`/mnt/external/demosaic/experiments/spectral-review-CPU-preflight-v3/receipt.json`,
SHA-256 `7e0e51976c373e9668dc20fa717b28b7a2e53ce6d04fefb9b57a49417504ad1c`.
The frozen quality package still uses all 46 actual original training modules,
including the original inverse-transform implementation.

At03:32UTC the original control endpoint passed an additional independent CPU
audit. All162 actual logs have finite loss/gradient and the exact original
schedule LR; all176 recorded forward/supervision observations agree; all46
archived model modules match. Model/EMA each have91 finite tensors and AdamW
has89 finite states at4,000 with nonnegative second moments. The final and
retained4k checkpoint hashes agree:
`d17891aa95cadfffe02dc497a96a9de3481f6044a3c270762bc014cbca0c16e4`.
See the [endpoint integrity receipt](results/spectral-control-original4000-integrity-v1.json).

Fresh spectral worker628726/1792467113.42 started at03:31:53UTC, from step0
with its original4k budget. Its initialization reports exact common parent
state/output and the pinned DINO hash. The first17 actual observation
dictionaries, through step25, match the completed control exactly. The fresh
arm and all quality/native-review requirements remain in progress.
