# Preserve V123 memory-guard state and repair dependent queues

Recorded: 2026-10-26T22:58:19-07:00 (America/Los_Angeles).

V123's original worker exited after the runtime memory guard observed22.9GB.
The emergency checkpoint actually contains all12,249 completed updates, including
96 model/EMA tensors,94 AdamW states and RNGs. A separate explicit continuation
waits for the active shadow pilot and its86-input-per-model evaluation to release
memory. It retains the original20k LR/update horizon and original worker-start
plus24h deadline, spending only7,751 more updates. V122 and all discarded checks
are reused. The original failure, logs, checkpoint and frozen sources remain intact.

All ten downstream owners had exited without starting their production/inference.
New dependency bindings retain frozen code and original deadlines, reduced by
elapsed time. V124/V125 reuse all four16+2 checks and wait for the recovered
frequency endpoint and its full review. At22:58 local, eleven repaired owners are
verified live; V123 is still waiting and V124/V125 have no production claims.

Two repair setup problems are preserved: a missing copied historical input
failed before launch; a wrong worker/controller selection was retired while
waiting for headroom, with no child or repeated model work. Corrected source
selection and input copying are covered by owned-process fixtures. Twelve focused
tests and Ruff pass. Saved-state CPU audit adds no neural/noise/RAW work.

[V123 recovery and current queue roots](../docs/v123-memory-guard-recovery.md) ·
[Checkpoint, owner and original-failure evidence](../docs/results/v123-memory-guard-recovery-v1.json).
