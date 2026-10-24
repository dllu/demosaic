# Optional band loss integration and V112 parameter checks

Recorded: 2026-10-24T08:09:52-07:00 (America/Los_Angeles).

Previous goal turn was progress: `7f720bd` completed the saved-output gradient
diagnosis and corrected stale baseline documentation. This turn revalidated
training 867877/1792848017.25 and its two waiting reviewers before new work.

Added optional normalized_band_weight to synthetic reconstruction losses and
both ordinary/grouped optimizer paths. Default 0 skips all band work. Positive
weights require sensor-valid clean camera targets, use unclipped sensor_target,
and reject paired references; paired training retains its existing objective.
The FP32 helper preserves the original 3-minus-9 band, 8-pixel border, all-neighbor
validity, .001 target RMS floor and .1 normalized epsilon. Target scale is detached;
empty/nonfinite target regions yield zero. Checkpoints serialize the validated
weight, legacy missing fields mean 0, and resume rejects changes. No ModelConfig,
inference interface or current recipe changes.

109 targeted tests pass in 11.51s. Two strengthened routing/resume tests then
pass in 3.48s, confirming nonzero synthetic terms and skipped default terms in
actual mixed-data training. A separate loader-contract regression passes in 1.11s.
All changed/new public Python sources pass Ruff. A source-frozen API replay
checks 108 saved cases and 42,467,328 gradient elements: all 108 baseline losses/
gradients and all 108 new band gradients match bit for bit, maximum difference 0.
That replay uses no network, noise generation, RAW decoding or CUDA.

A native 256 CPU parameter study uses actual V112 EMA, 2 deterministic training
strata, contrasts .025/1 and ADC/ISO12800: 8 new model/encoder forwards and 24
backwards. All 91 initial EMA tensors and official Tiny identity match. Weights,
configuration and Torch RNG remain fixed. NumPy64/Torch64 independently check
per-layer Gram entries, max absolute discrepancy 1.73e-11. Full gradients on two
predeclared faint/high-noise cases are retained; independent NumPy rereading
verifies 534 FP32 tensors, shapes, hashes and Gram entries with zero discrepancy.
Other cases retain streamed per-layer hashes/Gram rather than full vectors.

Parameter correction alignment improves in 5/8 cases, declines in 3/8, including
both faint high-noise cases. Faint ADC cosines change .177224->.196157 and
.257024->.272298; high-noise values change −.404351->-.405093 and
.163447->.149787. This limits the earlier output-space result: it is not a
trained quality gain or an optimizer-step prediction. The option stays off.

Eight additional discarded V112 CPU64/B1/FP32 updates pass on actual paired,
native and Commons data. Four paired batches omit the band; four synthetic
batches include it. Initial 91 EMA and first prediction/paired loss match the
original CPU control; all 8 step/domain/input/LR rows match without control
retraining. All 89 AdamW states reach 8, with finite model/EMA/Adam and frozen
encoder without gradients. The first attempted fixture omitted the explicit
parent initializer and stopped before any forward/update. Its source/log/
zero-work receipt and partial output remain intact; corrected v2 uses a fresh
output root. There are no validation forwards or new production jobs.

During final interface review, found a real queued-evaluation bug: collector
called verify_backbone_identity without its required legacy_sha256 keyword.
This would fail after loading an endpoint, before inference. Added an explicit
per-checkpoint helper and tested the real required-keyword interface with a
nonlearned module; bad model/revision/hash and missing metadata are rejected.

Prepared evaluation-v3 from the original frozen evaluation-v2 sources. Only
scripts/collect_quality_predictions.py changes among original execution files;
an additional regression-test snapshot is frozen. Core model/training/observation
sources, data, counts, limits and controls remain unchanged. Verified exact old
reviewers 925140/1792851360.58 and 868302/1792848232.8 were waiting, with no children
or completed stages. Sent SIGINT only to those owned idle roots and confirmed
their terminal statuses/exit. Their pending/terminal evidence and source bytes
remain preserved. No successful learned evaluation was repeated.

New evaluator 986158/1792855221.87 and independent audit 986159/1792855223.35 are
confirmed live/idle. They wait for original training 867877/1792848017.25, which
continues untouched. New source/output roots are V112-continuations-evaluation-v3
and V112-continuations-independent-audit-v2 under the same cache parent.
The evaluation uses queue-plan-v2.json; initial unexecuted preparation is also
preserved. No mutable test path or current-model choice pins the new queue.

[Optional API and mixed V112 parameter evidence](../docs/contrast-normalized-band-supervision.md) ·
[Integration/actual-CPU/API receipt](../docs/results/normalized-band-integration-v1.json) ·
[Idle reviewer supersession/source/launch receipt](../docs/results/evaluation-backbone-interface-fix-v1.json).
Private sources and state: .cache/current-quality-20261023-v1/
normalized-band-integration-v1/ and evaluation-interface-fix-v1/.
Broad real-photo superiority, fine detail and 100MP/10s remain open; current
V112 choice and the original Tiny/Small training budgets remain unchanged.

Final verification at 2026-10-24 08:26 PDT: all 22 frozen plan guards pass,
including historical attempts and current training/evaluation/review sources.
Both superseded reviewers are terminal with empty completions; new owners
986158/1792855221.87 and 986159/1792855223.35 remain live without children.
Training 867877/1792848017.25 is live with V114 at logged step 8575. Public source
bindings, local documentation links, all eight public Python Ruff checks and
whitespace checks pass. V112 remains selected. No test or neural result was
repeated for final bookkeeping.
