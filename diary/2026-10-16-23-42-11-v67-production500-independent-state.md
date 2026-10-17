# V67 actual production checkpoint500 independently verified

Previous goal turn was progress: completed/pushed V66 quality review and genuine
joint CPU/CUDA checks, launched V67 and its serialized review. Revalidated all
four real process identities at turn start; actual trainer progressed275→500.
The new 500-update evidence is an engineering checkpoint audit, not quality.

Copied the first production last.pt only after actual step500 validation/save,
verified source/copy SHA before and after, and preserved original metric lines
through500 without later rows. Both trainer/controller remained live before and
after the CPU-only check. Production B16/native256/BF16/workers4+2+2 has finite
94 model/94 EMA/92 AdamW states; all92 restoration tensors changed in model and
EMA, both normalization buffers remain exact. Moment shapes/steps and all21
logged LRs are checked against the original10000-update schedule. Last LR is
9.963796657738579e-5, not a retimed500/2000 schedule. Actual V66 EMA initializer,
fc0297 source bundle rebuilt from archived bytes, four manifests/protocol/RNG/
recipe/logs and all immutable production-plan guards pass. No CUDA initialized
by this independent process and no inference or target fitting.

Frozen checkpoint SHA256:
606eb69081b1c346cc4d8d9653171447da5c31966a435408a9e21cea8fc074a9.
External audit SHA256:
c3755c2755b2da28d53aaf702f29913d40c6e7c3ff2ee3503e56ebdc6f28f3c1.
Public receipt: docs/results/raw-kernel-phase-joint-v67-first500-state.json.

Reconciled stale reconstruction/completion documentation with completed V65/V66
reviews and the separately launched V67 stage, retaining quality/speed goals as
unmet. No quality result, native-view claim, promotion, stopping or schedule
change follows from this intermediate saved-state audit. The declared first2000
quality review and actual owner-exit gates remain in force. No production model
code changed; JSON/local-link/whitespace checks only are appropriate for this
receipt/documentation update.
