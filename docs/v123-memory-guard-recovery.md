# V123 saved-state continuation

**V123's saved-state continuation is running, starting at update12,250.**
The emergency checkpoint retained all12,249 updates after a22.9GB memory-guard
stop. The continuation spends only the remaining7,751 updates within the
original20k horizon and worker deadline. The
[shadow pilot and fixed-input review](reviewed-shadow-pilot-quality.md) are complete.
V120 remains the general recommendation; there is no new endpoint-quality claim.

[Actual resumption and current queue verification](results/v123-admission-resumption-v2.json) ·
[Verified durable13,000-update checkpoint](results/v123-resumed-step13000-v1.json) ·
[Original saved-state audit](results/v123-memory-guard-recovery-v1.json) ·
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

The actual13,000-update checkpoint is now preserved as an immutable hardlink.
All96 model/EMA tensors and94 AdamW states are finite, every AdamW counter is
13,000, and parent lineage/source digest still match. It contains751 new updates
beyond the emergency checkpoint. The worker continued afterward; this
saved-state check added no neural/noise/RAW/optimizer work and supplies no
new image-quality claim.

The original checkpoint, logs, failure and frozen plans remain unchanged.
Continuation outputs use a separate directory under the original frozen
workspace. V122's completed20k endpoint and all implementation checks are reused.
No completed training prefix or old prediction is rerun.

## Scheduling and dependent work

An explicit admission handoff changed the launch threshold from56 to52GiB:
16GiB allocator allowance +4GiB host overhead +32GiB planning reserve. The actual
V123 implementation check peaked at8,624,142,848 allocated bytes and
10,095,689,728 reserved bytes. The16GiB allocator cap and32GB runtime floor
remain. Before replacing it, the exact old waiter was stopped and verified to
have no child or continuation claim. Its retirement receipt is preserved.

The new worker passed the saved RNG/model/AdamW/encoder assertions before its
first actual forward and completed update12,250, with later updates observed.
The frozen controller/worker source bytes are identical to the preceding
continuation plan. Only launch admission and owner bindings changed.
The continuation's deadline is the original V123 worker start plus24h,
**including the interruption**; it receives no fresh24h allowance. Failure ends
this explicit attempt without an automatic retry. The original absolute
headroom-wait deadline is also retained.

All ten original downstream controllers also exited after the producer failed.
Their old receipts are preserved. Fresh dependency bindings retain frozen code,
inputs, comparisons and worker limits. Every original dependency observation
deadline is reduced by elapsed time rather than reset. No downstream quality
inference or V124/V125 production had started. Both arms reuse their four
completed16+2 CPU/CUDA checks, and retain their original20k production budgets.

Current local roots beneath `.cache/current-quality-20261023-v1/`:

| Work | Current root |
| --- | --- |
| V123 continuation | `learned-frequency-training-recovery-v2/run` |
| V122/V123 evaluation | `V122-V123-learned-frequency-quality-recovery-v2` |
| Independent audit | `V122-V123-learned-frequency-independent-audit-recovery-v2` |
| Saved comparisons | `V122-V123-learned-frequency-matched-review-recovery-v2` |
| Both green-mesh profiles | `V122-V123-green-mesh-review-recovery-v2` |
| V124/V125 training controller | `conditional-mean-training-recovery-v4/run` |
| V124/V125 evaluation | `V124-V125-independent-noise-quality-recovery-v3` |
| Independent audit | `V124-V125-independent-noise-independent-audit-recovery-v3` |
| Saved comparisons | `V124-V125-independent-noise-matched-review-recovery-v3` |
| Both green-mesh profiles | `V124-V125-green-mesh-review-recovery-v3` |
| Repeated-noise supplement | `V124-V125-conditional-response-recovery-v3` |

An initial dependency-repair preparation missed a bound historical input and
failed before launch. A subsequent attempt selected the worker entrypoint in
place of the adoption-aware controller. It was retired while still waiting for
headroom, with no child or repeated model work. These partial attempts and their
receipts remain preserved. The corrected runner copies bound historical inputs,
selects the original controller entrypoint and verifies actual owner identity.
Twelve focused tests include owned subprocess launches, failure without retry,
expired deadlines, immutable inputs and rejection of already-started stages.
