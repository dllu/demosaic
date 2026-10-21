# Complete matched V43 training and start full quality evaluation

Recorded: 2026-10-21T13:56:38-07:00 (America/Los_Angeles).

The existing V95 worker reaches 20,000 updates, completes all five scheduled
validations and exits; its controller exits after the full matched observation
audit. V93, V94 and V95 are now all complete under the original frozen numerical
plan. The actual disk-reserve suspension after 8k did not require a training
restart. The earlier two unsaved attempts remain archived with their original
generic errors; their triggers are still unknown.

Run the independent saved-state/trace auditor on V95 with CUDA hidden. It checks
all six retained files, correct optimizer counters, finite model/EMA/Adam states,
canonical original V43 architecture, original initializer and DINO hashes,
fixed curated membership, all 801 recorded training rows, exact first 24 CUDA
probe inputs and five validations over all 28 condition/CFA cells. Counts are
20,000 training forwards, 160 validation forwards, 20,160 DINO calls and 20,000
optimizer steps. The final EMA is primary; the separate validation-best file
also records step 20k. The matched controls retain their earlier passed audits.

V95 final checkpoint SHA:
`189f5530ef8be6384e101e00fe50ece19297436b0c65b5bb3cabbb2f327e2bb6`.
Independent audit SHA:
`c8a976b803c66502d65dd8cb8d5bddb26b6a3c0b1c09b0ba30e8016a9384cc8f`.
The completed training observation audit verifies 390 identical paired/native
control rows and 197 identical paired rows for the fine-detail treatment.
These are engineering checks, without a held-out quality conclusion.

Prepare the full seven-stage evaluation only after the training owners exit.
Local root:
`.cache/quality-first-20261020/V43-curated-matched-evaluation-v1/`.
External artifact root:
`/mnt/external/demosaic/v43-curated-evaluation-20261021-v1/`.
Plan SHA:
`c91234f3f80521324e33d0e2b3a8953fe64f047b2ba9be58b422cd5b9957dafa`.
Freeze all four primary checkpoint bytes, original trained source, evaluation
helpers, protocol and 1,787 declared inputs. The photo suite is the full 427
photos plus 16 procedural sources, seven conditions/four CFAs, nine methods
including both input-only RawNIND gain adapters, with expected 111,636 metric
rows. Known/unseen measured-CFA panels, weak-detail/flat carriers, color grid,
standing GFX and highlight crops follow serially. Fresh IEEE FP32, unchanged
resource floors, bounded disk suspension and no automatic retry/promotion.

Launch actual controller PID3661140/create1792616184.0; the photo worker
PID3661319/create1792616248.47 starts after the stable-headroom interval. The
immutable launch observation contains two complete photo batches: eight sources,
2,016 score rows and all nine method labels, with all present metrics finite.
These partial records do not establish comparative quality. The evaluation
already shares immutable checkpoint snapshots across panels, so preserving the
external reserve does not require changing report or numerical behavior.

Publish the [V95 saved-state audit](../docs/results/v43-quality-V95-completed-training-v1.json)
and [actual full-evaluation launch](../docs/results/v43-quality-full-evaluation-launch-v1.json).
Shorten the main study's resource-recovery history while retaining all evidence
in its validation appendix and immutable receipts. Current documentation marks
all training complete and full quality review in progress. V43 remains the
working reference; actual complete numerical/native review is required before
any promotion. Speed work stays deferred and full PROMPT completion is unproven.

