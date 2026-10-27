# Reviewed-photo quota trial and early resume validation

Recorded: 2026-10-27T09:36:16-07:00 (America/Los_Angeles).

Previous goal turn: progress. Commit `de6f3d6` verified319,824 source metadata
selections and documented the difference between corpus size and finite-schedule
visitation. This turn implements the next controlled quality comparison rather
than inferring restored quality from those counts. The full PROMPT goal remains
open: finest weak detail, dark-field behavior, broad RawNIND superiority and
100MP/10s are still unproven.

V133 changes the photographic reviewed quota from V131's.5 to.05, keeping the
V120 Small EMA parent,90781 photos/29 regions, seed70, native256/B16/BF16,
single noise view, zeroPSF, native128/paired32 and full20k LR horizon. Original
V131 training/check receipts are reused without another control run. The newer
prepared90780/31 data remain separate so the comparison isolates quota.

Both device checks are complete: actual CPU128/B1 and CUDA256/B16 each16+2
updates, for36 discarded training/encoder/optimizer calls and306 clean slots.
Across both stages,262 unaffected examples match141,054,572 prepared values
exactly against the original V131 inputs. CPU matches15 whole B1 batches;
CUDA matches all nine native/paired B16 batches and103 unaffected Commons
examples in its nine changed Commons batches. CUDA peak allocation is
7,041,804,800 bytes. Timing is not treated as a throughput comparison.

The initial CPU check uncovered an existing guard-order problem. It trained16
updates, preserved step16, then its changed-quota rejection reached the model
construction hook before `require_resume_rois` ran. That hook stopped before
constructing the rejected model or executing a rejected forward. The original
controller exited with its failure, logs,16 inputs, state and source intact.
The original root is
`.cache/current-quality-20261023-v1/reviewed-quota-training-v1/run/`.

`require_resume_rois` now runs with the earlier resume checks before model
construction. All62 other training modules match V131 bytes; reversing just
this guard relocation restores the entire old `train.py`. Valid training math
and data order do not change. The existing actual tiny-CPU interrupted/resumed
training test now forbids construction for changed quota and changed catalogue.
The focused78-test run passes in16.82s; Ruff passes.

The explicit continuation uses only the remaining two CPU updates from the
actual16-step checkpoint, with no prefix replay, Adam reset or LR restart.
Actual changed-quota and changed-catalogue rejections both occur before model
construction. The16→18 continuation finishes within the original absolute CPU
check deadline, epoch1793119790.34, without extending its30-minute budget.
Original failure receipts retain their bytes. New CUDA executes its original
16+2 budget under the corrected source; its quota-resume rejection passes.

The recovered root is
`.cache/current-quality-20261023-v1/reviewed-quota-training-recovery-v2/run/`.
`plan.json` preserves the prepared worker plan; `controller-plan-v1.json` adopts
only the completed CPU check and retains all original remaining budgets.
`CPU-continuation-plan-v1.json` binds the old state/failure/deadline. The new
training controller is PID2423684/create1793118798.17. It has both check receipts
and waits for the exact original V131/V132 controller to finish both full arms
and exit before production. The optional completed-only dependency mode defaults
off for other controllers; their frozen source and behavior are unchanged.

Independent constructor-free inspection loads all four actual16/18 states,
checking526,475,668 finite model/EMA/Adam values,91/89 tensor/state counts,
optimizer steps, parent/seed/quota/full horizon and completed input proofs.
This audit constructs/calls no neural module and leaves CUDA uninitialized.
It adds no model score. No original mean or spatial job is signaled or edited.

A live early-review queue is prepared under
`.cache/current-quality-20261023-v1/V133-progress1000-quota-review-v1/`,
with PID2424110/create1793118975.9. It plans102 new V133 FP32 root/encoder calls
at immutable progress1000 within the same20k worker/horizon:64 saved shadows,
16 ordinary materials, four main-GFX512 contexts, two extra-mesh768 profiles
and16 faint ADC observations. It adopts the original102-input preflight after
exact observation and source-compatibility checks. V120 and original V131
progress predictions are reused, never rerun. Saved-control adoption checks
input arrays/fingerprints, target/reference, ROI, exposure and noise metadata;
partial/duplicate/changed observations are rejected by tests.

CPU reporting and independent FFT/native-pixel auditing follow collection.
At least two exact synthetic native100% triplets and both real GFX scenes are
included in the retained reporting path. DSCF3880 and corrected DSCF3835 ISO100
references remain qualitative/nonexact; originals and siblings stay read-only
and outside training. Current live queues have no new inference or noise yet.
Full20k primary/full-frame comparison remains to be arranged once the endpoint
is available; early support is not a full benchmark or SOTA claim.

Production remains20,000 updates/640 validation/20,640 encoder calls/320,000
clean slots, with a retained1000 snapshot and no schedule reset. It uses52GiB
admission,16GiB CUDA cap,32GB runtime floor,48h worker and eight-day dependency
wait bounds. The early queue uses52GiB admission/12GiB CUDA cap/32GiB runtime
floor and102 calls. The public setup receipt is
`docs/results/reviewed-quota-training-setup-v1.json`; current guides/README link
`docs/reviewed-quota-training.md`. V120 selection and all56 performance plot
points remain unchanged. Trained quality and actual native viewing are pending.

Final publication checks pass174 local links and1,518 frozen bindings across
12 plans, with nine exact live controller/queue owners verified. V133 has no
production claim or quality calls yet. Both implementation checks, independent
saved-state inspection, source compatibility and the current selector pass.
