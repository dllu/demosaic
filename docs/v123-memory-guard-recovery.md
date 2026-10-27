# V123 saved-state continuation

**V123 stopped safely at update12,249 after available system memory fell to
22.9GB. Its emergency checkpoint retains every completed update.** A separate,
explicit continuation waits for the V126/V127 pilot and its fixed-input
evaluation to release memory, then runs only the remaining7,751 updates.
V120 remains the general recommendation; there is no new endpoint-quality claim.

[Recovery and queue verification](results/v123-memory-guard-recovery-v1.json) ·
[Saved-state continuation runner](../scripts/resume_frequency_training.py) ·
[Dependency repair](../scripts/rebind_unstarted_quality_queue.py).

## Retained training state

The failed original controller and worker have exited. Its failure receipt counts
12,249 prepared batches, training forwards and AdamW updates,384 validation
forwards and12,633 encoder calls. The emergency `last.pt` has step12,249,
96 finite restoration/EMA tensors in each state,94 finite AdamW states all at
12,249, and saved Python, CPU-Torch and CUDA RNG states. Its SHA256 is
`6a07072c67822a8f546df096187e604b4dde8de054c2e3f7bdbf86bbac68d3d4`.
The last fixed eight-source validation panel is at12,000; it is not a full427-photo
endpoint evaluation.

The continuation uses the original frozen source, parent lineage,90,786-source/
fourteen-region cohort, seed66, batch16/native256/BF16, learning-rate horizon,
EMA and losses. Its first actual batch must be12,250. Before that batch's sensor
preparation, saved RNG states must match; before its first model forward,
all96 restoration tensors and94 AdamW states must match the checkpoint exactly.
The original source digest and official frozen Small encoder are checked again
at completion. Final counters combine the original prefix with the observed
continuation, requiring exactly20,000 optimizer updates and640 validation calls.

The original checkpoint, logs, failure and frozen plans remain unchanged.
Continuation outputs use a separate directory under the original frozen
workspace. V122's completed20k endpoint and all implementation checks are reused.
No completed training prefix or old prediction is rerun.

## Scheduling and dependent work

The original56GiB launch threshold,16GiB allocator cap and32GB runtime floor
remain. The continuation's deadline is the original V123 worker start plus24h,
**including the interruption**; it receives no fresh24h allowance. Failure ends
this explicit attempt without an automatic retry.

All ten original downstream controllers also exited after the producer failed.
Their old receipts are preserved. Fresh dependency bindings retain frozen code,
inputs, comparisons and worker limits. Every original dependency observation
deadline is reduced by elapsed time rather than reset. No downstream quality
inference or V124/V125 production had started. Both arms reuse their four
completed16+2 CPU/CUDA checks, and retain their original20k production budgets.

Current local roots beneath `.cache/current-quality-20261023-v1/`:

| Work | Current root |
| --- | --- |
| V123 continuation | `learned-frequency-training-recovery-v1/run` |
| V122/V123 evaluation | `V122-V123-learned-frequency-quality-recovery-v1` |
| Independent audit | `V122-V123-learned-frequency-independent-audit-recovery-v1` |
| Saved comparisons | `V122-V123-learned-frequency-matched-review-recovery-v1` |
| Both green-mesh profiles | `V122-V123-green-mesh-review-recovery-v1` |
| V124/V125 training controller | `conditional-mean-training-recovery-v3/run` |
| V124/V125 evaluation | `V124-V125-independent-noise-quality-recovery-v2` |
| Independent audit | `V124-V125-independent-noise-independent-audit-recovery-v2` |
| Saved comparisons | `V124-V125-independent-noise-matched-review-recovery-v2` |
| Both green-mesh profiles | `V124-V125-green-mesh-review-recovery-v2` |
| Repeated-noise supplement | `V124-V125-conditional-response-recovery-v2` |

An initial dependency-repair preparation missed a bound historical input and
failed before launch. A subsequent attempt selected the worker entrypoint in
place of the adoption-aware controller. It was retired while still waiting for
headroom, with no child or repeated model work. These partial attempts and their
receipts remain preserved. The corrected runner copies bound historical inputs,
selects the original controller entrypoint and verifies actual owner identity.
Twelve focused tests include owned subprocess launches, failure without retry,
expired deadlines, immutable inputs and rejection of already-started stages.
