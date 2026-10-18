# Complete both directional budgets and start quality review

Previous goal turn made progress by correcting stale requirements and verifying
V79 step 3,000. This turn repeatedly verified the same actual V79 child by PID
and creation time while waiting for its original remaining updates. No restart,
extension, recipe, source, metric target or quality criterion changed.

Both V78/V79 now complete their full original 4,000-update schedules. Controller
404904/1792353195.14 and final child 444533/1792356217.53 have exited successfully.
V78 final SHA256 is
`26e43921d2f4f46b39d9385c8399699f9fe1f0294f34efa4e6da0d4ad9baa7c4`;
V79 is `2f3e567e4bca7bf308f79d5e613d791d612e7d950c0cd64c9c21ac548aa1f11f`.
Each processes 64,000 example draws. Every final state has finite 99 model / 99
EMA / 97 AdamW entries with correct counters/shapes. The independent boundary
also verifies all 89 common trainable model/EMA tensors changed from the parent
and only normalization buffers stayed equal. All eight scheduled checkpoints
remain retained; all 25,800 scalar moments are nonzero at each milestone.

Re-read actual final checkpoints and logs. All 176 complete sampled records
match exactly, as do all 161 logged step/domain/LR/full-batch fingerprints.
Actual initial common EMA, local branch hash and frozen official DINO captures
match. Model config, Torch version and final Python/Torch/CUDA RNG states match.
Only interval weight and the run-specific output/source/protocol snapshot paths
differ in saved configs. Source bundle is identical3eb9e74e…; archive protocol
bytes match. This does not establish bitwise GPU reproducibility or equality of
all unlogged tensors. Keep the observed first-step base-loss variation and
single-trajectory/source-bootstrap caveats in final interpretation.

Extended independent scalar accounting to the full logged history. The interval
term remains candidate-synthetic-only, omitted on paired RAW. NumPy FP32 rebuilds
all 238 nonpaired logged total losses across both arms exactly (maximum error0).
No evaluation scores were used to change the recipe.

Evaluator405679/1792353257.72 observed exact successful training-owner exit,
passed its independent final boundary and began real primary inference. Known
panel completed and unseen is live at capture. The owned CPU watcher completed
all eight retained boundaries. CPU saved-array/native closure and working V43/
RawNIND reference supplement remain queued behind successful evaluation. Final
full427/procedural/source/color/analytic/GFX inference, numerical and actual
native viewing/publication closure remain required; no quality gain or promotion
is inferred from completed training. Only an eligible improved candidate gets
new full101.996MP FP32/16-bit/timing work. Goal remains active, SOTA and the
requested large real-photo advantage/unproven speed target remain outstanding.

See [completed training](../docs/directional-interval-original4k-training.md) and
[bound receipts](../docs/results/directional-interval-original4k-training-complete-v1.json).
