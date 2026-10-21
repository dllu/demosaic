# V95 reference-observation consistency checks prepared

Recorded: 2026-10-21T16:41:00-07:00 (America/Los_Angeles).

Revalidate the actual V96 worker PID3845032/create1792625778.91 and controller
PID3838388/create1792625353.89. Both are live; production reaches step500 with
finite loss/gradient, and the recorded resource floors hold. V97 is queued
serially under the same frozen plan. Full quality/default status is unchanged.

Prepare an additional evaluation consistency gate for the shared V43/V95
references. The new four-model comparison orders V43/V95/V96/V97, while the
reviewed comparison orders V43/V93/V94/V95. Pin the earlier evaluation plan
and all seven stage receipts when preparing the palette evaluation. Require
exact full model hashes, DINO/forward counts, observation counts and sampled
physical-input hashes for both shared references, mapped by their verified
checkpoint identities. Fresh prediction computation remains mandatory.

Thirteen tests pass, rejecting altered weights, call counts, coverage and
input samples in either reference position. Replay the actual saved reference
metadata from all seven reviewed stages in the proposed order; all pass.
This CPU metadata replay does not load new models, run inference or supply
new quality evidence. The live training source/configuration is untouched.
Archive the executed replay producer and publish the
[preparation receipt](../docs/results/v95-palette-reference-witness-preparation-v1.json),
SHA `7c439e9d476e5f8dc1e5f4132a4be05bb2e873d948f51db9fc8be6eae42e39a6`.

The final4k saved-state audits and full primary/analytic/color/GFX/native
review remain pending. V43 stays the working reference, and speed stays
deferred. This is evaluation preparation, not model promotion or completion
of the full PROMPT objective.

