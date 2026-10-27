# Complete endpoint review queues for the photographic quota trial

Recorded: 2026-10-27T10:21:16-07:00 (America/Los_Angeles).

Previous goal turn: progress. Commit `4a95f55` queued the quota-only V13320k
trial and102-input progress review, with actual CPU/CUDA16+2 checks and the
real ROI resume-validation fix. This turn fills the remaining full-endpoint
review gap without changing any training, source, parent, data or old budgets.
The PROMPT objective remains open; no new model-quality result is available.

Four live source-frozen queues now wait in dependency order:
`V133-reviewed-quota-quality-v1` (PID2476176/create1793121325.18),
`V133-reviewed-quota-independent-audit-v1` (PID2476178/create1793121326.42),
`V133-reviewed-quota-comparisons-v1` (PID2476181/create1793121327.88),
`V133-reviewed-quota-green-mesh-v1` (PID2476448/create1793121475.9).
All are under `.cache/current-quality-20261023-v1/`; their launch receipts
bind exact owner creation times, plans and frozen sources. All currently wait,
with no quality forward, RAW decode, noise simulation or optimizer update.

The evaluator now follows the actual live controller's plan reference rather
than assuming `plan.json`. V133's adopted controller uses `controller-plan-v1.json`.
The new quota format declares only V133, verifies its completed20k/91-tensor/
89-Adam-state endpoint and every explicit frozen recipe setting, then requires
its completed unaffected-input comparison. Genuine18-step data are rejected;
positive full20k quota contracts remain unit fixtures until actual training ends.
No partial candidate is relabeled as complete and no old neural model is replayed.

The planned full collection is4,586 V133 root/encoder calls across eight stages:
photo3,108 (12,404 observations), known24 (72), unseen30 (90), texture112 (448),
color1,176 (1,176), main GFX4, highlights2, full GFX130 batches (520 tiles).
The numerical audit covers14,190 observations; all retained observations including
real GFX tiles total14,716. These are repeated source/noise/CFA conditions rather
than independent photographs. Two more CPU FP32 root/encoder calls cover the
extra fine-mesh profiles. The separate102-call retained-progress budget is intact.

V120/V117 completed metrics and predictions are reused. V131 is resolved only
from its original completed independent audit, exact owner, training plan and
checkpoint. The full numerical/local/native comparisons are V120→V133,
V117→V133 and V131→V133. The quota-only V131/V133 GFX contrast requires matching
conditioning,32px grid and every actual input fingerprint for all130 full-frame
tile batches. Older V120/V117 profile/grid differences remain labeled and do
not isolate a model-only effect. Source/ROI/WB/matrix/exposure stay matched.

The independent CPU audit and comparison path retain all427-photo local-detail
support, at least two native100% noisy/restored/exact-synthetic-GT triplets,
all six main GFX regions and complete linear/sRGB RGB16 export verification.
The mesh queue adopts existing V120 predictions and original V131 predictions
when ready under both fixed profiles. Nine control predictions are reused;
only V133 receives two new768px-context CPU forwards. It renders V120/V131/V133
native160 boards/triplets at+4EV. Main DSCF3879/3880 and additional3842/corrected
3835 sources/JPEGs/siblings stay cached, read-only and outside training; ISO100
AHD/JPEG references are qualitative, not exact GT. Actual viewing is pending.

The metadata preparer's first mesh call supplied an input-metadata receipt
where the existing API needs a completed inference receipt. It failed before
creating the mesh queue or running inference. `prepare-v1.py` and its log remain
unchanged; the three already live queues were preserved. The explicit mesh-only
continuation resolves the exact inference templates from the original mesh
plan's bound inputs and creates just the remaining queue. No model, worker,
old control or partial stage was restarted or rerun.

A constructor-free preflight verifies the genuine partial-checkpoint rejection,
62 byte-exact training modules plus the existing pure train.py guard relocation,
five byte-exact inference helpers and byte-exact independent metric math. The
two actual completed V120 mesh profile predictions are adopted with original
observation/conditioning and checkpoint hashes. Future V131 and V133 actual
full-frame matching remains pending. This preflight adds zero neural/noise/RAW
or optimizer calls and leaves CUDA uninitialized.

Focused validation:127 tests pass in5.09s, covering actual-archive one-model
support, all required endpoint-state gates, controller plan identity, deferred
owner/audit binding, partial/corrupt control rejection, every tile-batch input,
mesh profile reuse and existing comparison paths. Ruff passes. No primary model
score, current-selector change or performance-history point is added.

Executed preparation/preflight sources and receipts are preserved under
`.cache/current-quality-20261023-v1/V133-full-review-setup-v1/`:
`prepare-v1.py`, `preparation.log`, `prepare-v2-mesh-only.py`,
`mesh-continuation.log`, `preparation-v1.json`, `preflight-v1.py`, `preflight-v1.json`.
The public receipt is `docs/results/reviewed-quota-full-review-setup-v1.json`.
Current V133/model/requirements/README pages now describe the full queued review
rather than leaving it to be arranged. New review dependency waits are bounded
to eight days; all original queue sources, observation deadlines and call budgets
retain their bytes. Quality and broad real-camera/SOTA/speed goals remain open.

Final publication verification passes98 local links and1,693 frozen bindings
across16 plans, with13 exact live controller identities and the original mean
worker verified live. The current selector is unchanged. Additional read-only
inspection of the genuine CUDA18 snapshot matches all explicit frozen CUDA
recipe values and production values apart from declared output/logging/protocol
path metadata; this is serialization compatibility, not a completed endpoint.
The latest V124 log is at11,125 updates. No new quality execution has begun.
