# V123 completed saved-state continuation

**V123 completed its original20,000 updates, and V122/V123 endpoint predictions
are collecting.** The saved12,249-update prefix was retained exactly; the
continuation performed only7,751 more updates. All96 model/EMA tensors and94
AdamW states are finite at20,000. Image quality remains unmeasured;
V120 remains the general recommendation.

[Completed training/final-state verification](results/v123-frequency-training-complete-v1.json) ·
[Quality-identity repair and current owners](results/v123-frequency-quality-identity-repair-v1.json) ·
[Original resumption evidence](results/v123-admission-resumption-v2.json) ·
[Preserved13,000-step checkpoint](results/v123-resumed-step13000-v1.json) ·
[Original emergency-state audit](results/v123-memory-guard-recovery-v1.json).

## Completed training and retained invariants

The original memory guard saved12,249 updates after available RAM fell to22.9GB.
Its checkpoint remains unchanged, SHA256
`6a07072c67822a8f546df096187e604b4dde8de054c2e3f7bdbf86bbac68d3d4`.
Before the continuation's first actual batch12,250, saved RNG states matched;
before its first forward, all96 model tensors and94 Adam states matched exactly.
Source, parent, EMA, LR horizon, seed66, native256/B16/BF16,90,786-source/fourteen-
region data and losses retained their frozen values. No prefix/check was repeated.

Final checkpoint SHA256:
`4e9f1165c57ee7b3955ffd1dba1dfc13df2b192fcc28f7b86b17a2c1ae8c1c8a`.
Totals are20,000 prepared/training/optimizer calls,640 validation calls and20,640
encoder calls. Domains are9,900 Commons/procedural,5,121 native and4,979 paired.
The continuation alone made7,751 training and256 validation calls. Official Small
encoder/source identity checks pass. The final state was independently reopened
on CPU without a model forward. The immutable13k snapshot and original failed
plans/logs/checkpoints remain preserved.

The completed worker retained its original start+24h deadline, including the
interruption. Actual admission was52GiB with16GiB CUDA cap and32GB runtime floor.
Peak allocated/reserved CUDA bytes were8,625,714,688/10,374,610,944. This is resource
accounting, not a speed comparison. [Continuation runner](../scripts/resume_frequency_training.py).

## Current endpoint review and dependent work

The first rebound photo collector stopped while loading a96-tensor frequency
checkpoint because its legacy identity assertion required91 tensors. Its archive
contains zero records/predictions and no root/encoder forward occurred. The
corrected collector takes each verified checkpoint's declared tensor count and
still requires exact EMA keys/values and the official encoder identity.
All frozen inference mathematics, inputs, checkpoints and stage counts remain
unchanged. The original first photo worker's12h absolute deadline is retained.

The corrected evaluator has progressed past loading and is writing new V122/V123
predictions. Nine downstream controllers have new exact owner/plan bindings;
all retain their original absolute dependency deadlines. V124/V125 reuse all
four completed16+2 CPU/CUDA checks and their original20k production budgets.
They wait for the original quality/audit/comparison/mesh chain; no production
update has started.

A second-generation rebind preparation exposed a receipt-name collision before
launch. The helper now preserves prior declarations/helpers under their original
names and writes a new numbered receipt/helper. Its regression test verifies
both generations' bytes and the identical absolute deadline. That partial
preparation remains preserved, with zero neural work.
[Identity/dependency repair source](../scripts/repair_frequency_quality_identity.py) ·
[Unstarted dependency rebinding](../scripts/rebind_unstarted_quality_queue.py).

Current roots beneath `.cache/current-quality-20261023-v1/`:

| Work | Current root |
| --- | --- |
| Completed V123 continuation | `learned-frequency-training-recovery-v2/run` |
| V122/V123 evaluation | `V122-V123-learned-frequency-quality-recovery-v3` |
| Independent audit | `V122-V123-learned-frequency-independent-audit-recovery-v4` |
| Saved comparisons | `V122-V123-learned-frequency-matched-review-recovery-v3` |
| Both green-mesh profiles | `V122-V123-green-mesh-review-recovery-v3` |
| V124/V125 training controller | `conditional-mean-training-recovery-v5/run` |
| V124/V125 evaluation | `V124-V125-independent-noise-quality-recovery-v4` |
| Independent audit | `V124-V125-independent-noise-independent-audit-recovery-v4` |
| Saved comparisons | `V124-V125-independent-noise-matched-review-recovery-v4` |
| Both green-mesh profiles | `V124-V125-green-mesh-review-recovery-v4` |
| Repeated-noise supplement | `V124-V125-conditional-response-recovery-v4` |

Historical recovery decisions are in the [local-time diary](../diary/2026-10-27-03-27-31-v123-complete-frequency-review.md).
The repair changes execution bookkeeping; it establishes no quality gain or
architectural recommendation.
