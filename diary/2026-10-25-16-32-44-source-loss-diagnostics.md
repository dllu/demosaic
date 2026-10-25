# Trace high-loss Commons draws without changing training updates

Recorded: 2026-10-25T16:32:44-07:00 (America/Los_Angeles).

Added optional source-loss diagnostics for future corpus cleanup. Setting
`source_loss_every` to a positive integer records existing Commons predictions
on the first optimizer update and interval updates. Default0 keeps the original
sample payload and loss/backward behavior; frozen V119 is unchanged.

The actual reader now optionally records source identity after exclusion retries
and reviewed-ROI overrides, cache path and manifest-declared hash, actual cache
rectangle before geometry, override rectangle, draw index/seed and source kind.
JSON strings collate across procedural/photo draws without consuming RNG or
reloading source bytes. Paired/native samples are omitted from this log.

Each diagnostic is a detached FP32 singleton reconstruction loss using the
configured masks/objective/epsilon/optional terms. It reuses existing predictions
without NN calls. These are not additive batch-loss contributions: highlight and
other mask denominators can differ. Noise/WB/matrix/CFA are recorded; hard noise,
saturation and detail can cause high scores, so exclusion still requires visual
inspection. The draw seed replays clean augmentation; noise replay depends on
the run's separate RNG policy. Joined forwards preserve group/example identities.

Validation:50 focused tests passed in19.41s, including closed-form mask-sensitive
scores and no neural-module calls during diagnostics. Actual CPU single/joined
mixed-domain training with diagnostics on/off and resume gives bit-identical
model, EMA, AdamW and random states. Existing archived-loop default and group
loss/gradient checks pass. After metadata paths were normalized to absolute,
the affected source-provenance test passed again in2.25s.

An actual native256 photographic draw from the90791 corpus independently observed
the cache load and actual slice: sourcef228e4ae9ec570a344d0f3d9df936fbb56d66a22,
cachebox[234,113,568,643], seed65/index0. Metadata matches that exact load/slice,
full cache SHA agrees, and Python/NumPy/Torch RNG remain unchanged. Neural-module
calls were forbidden; no RAW, noise or optimizer work occurred in this read proof.
This is implementation evidence, not a model-quality result. Executed source
snapshots and [receipts](../docs/results/source-loss-diagnostics-v1.json) are
preserved; [usage and limitations](../docs/source-loss-diagnostics.md) are current.

The new V119 fine-mesh follow-up was also prospectively queued in private scratch
before viewing its endpoint. It waits for original20k training and the original
quality queue's immutable copy, then runs exactly two new CPUFP32 operators on
the same saved768px input: nominal prior and fixed DSCF3879 profile. Five nominal
and two nearby-profile control predictions are retained, with no repeat control
NN, source decode or fresh noise. Pure preflight rejects changed owners and
19,999-step accounting. This queue leaves all earlier jobs unchanged. Native
review and performance reporting remain pending; the full project goal is open.
