# Verify the first V93 production checkpoint and scheduled validation

Recorded: 2026-10-20T22:34:04-07:00 (America/Los_Angeles).

V93 completes its first scheduled validation at step4,000 and retains
`/mnt/external/demosaic/v43-curated-training-20261020-v1/train/V93/step-004000.pt`,
SHA256 `bc7b547646a37f82a98d4ee7662829bf11649cd3b2aea7d2e9ad18985633e121`.
The same original controller PID2355916/create1792554876.82 and production
worker PID2430283/create1792558558.82 remain live; the independent observation
confirms training continues through logged step4,550, with later status already
past4,600. Neither process was restarted.

An independent CPU-only audit verifies the retained checkpoint hash twice,
its byte identity with `last.pt` at the observation, optimizer step4000, all
71 model/71 EMA finite tensors and69 finite Adam states with counter4000.
Restoration tensor keys exactly match original V43; both model and EMA have
changed from the initializer. The parent is the original step2000 checkpoint
`0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5`.
The small curated manifest, original native/paired/validation/protocol hashes,
seed56/B16/native256/BF16/20k settings, source hash and frozen-input guards pass.
The auditor performs no model inference or training and never initializes CUDA.

The first audit stopped at a literal configuration-dictionary comparison:
the old V43 schema omits19 fields added by later experiments. There are no
different shared fields. Loading both through the frozen `ModelConfig` proves
their effective settings match, and exact tensor keys confirm no restoration
head was added. A fresh v2 auditor records those defaults and preserves the
failed v1 source; this corrects the audit rather than changing training or
relaxing architectural equality. Successful audit receipt:
`973fbd64e5ae0a76c6e2eeb61d077c8436dd492006771dec268027300b7b68b6`.

All161 scheduled training metric rows through4,000 exist: step1 and then
every25 updates. Recorded losses and gradient norms are finite. Scheduled
validation completes eight sources under seven conditions/four CFAs, all28
cells/224 observations, with finite present metrics; absent-region metrics
remain null. Its complete event is retained as a private immutable snapshot.
This is the routine training-validation subset, not the fixed427-photo primary
test or a matched quality comparison. Its means do not justify promotion or
comparison with historical full-panel means.

[Published checkpoint/validation engineering evidence](../docs/results/v43-quality-V93-first-production-checkpoint-v1.json)
records the actual snapshot and its scope. Updated the validation guide. The
original three-arm plan continues unchanged; V94 and V95 follow V93 serially.
Final20k EMA remains primary, with diagnostics and training-validation best
separate. Full endpoint evaluation and actual native crop review remain pending;
V43 remains the working reference and speed work stays deferred.

