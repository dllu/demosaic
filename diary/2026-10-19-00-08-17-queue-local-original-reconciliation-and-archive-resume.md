# Queue local-original reconciliation before broader archive downloading

The previous turn recovered and independently verified168.82GiB of external
storage. This turn preserves that progress for additional Commons data while
the original V83 schedule continues. At observation, all1,188 local originals
are downloaded (17,175,771,412bytes), detached is live at step2,025/4,000, and
the new handoff waits for the exact local downloader/preparer exits and successful
preparation. All486 frozen training/review sources remain exact, as do PROMPT,
README, predeclared criteria and the general archive read-only write guard.

Added a narrow archive handoff: bind all immutable attribution/source fields,
publish only new checksum/size-verified originals, reuse valid existing entries,
and update only selected operational index fields in one guarded transaction.
Existing archive images and local originals/index stay read-only. Record before/
after rows and exact status-count changes; failed local sources remain pending.
An idempotent repeat does not duplicate files or attempt counts. No original
image overwrite or active training membership change.

The same shared archive lock covers reconciliation and the existing frozen
download-only CLI. Settings are2 workers/.25 request starts per second,
608GiB reserve and10,000-file limit, preserving headroom for caches/model work.
The controller records child identity and exit. Actual owner3126300 /
1792393569.12 is live/child-free, CPU nice10/idle I/O, no Torch/CUDA libraries
while waiting. Its main-index snapshot still matches the original local
selection snapshot; no production archive update or broader download has begun.

Eight integrity/metadata/idempotency/rollback tests pass in2.87s. A complete
frozen-worker fixture uses two real cached Commons originals and a separate
fixture archive/lock. It copies and indexes both, preserves attribution and
runs the actual unchanged downloader with no pending records; that child exits0
without image downloads. Source originals and production archive are unchanged.
Preflight receipt SHA25680e2538a4c6c54902485160c7e36a1c183902c0df67a5fa9f60a0ceba3708bb9.

Actual queue: `.cache/commons-archive-handoff-20261019-v1/`.
Plan SHA2565a5ee8af4067213adbd8432c35c37a598f1def5ba3295956562f81819d8ad5be.
Published receipt: `docs/results/commons-archive-handoff-queue-v1.json`.
Local preparation, production reconciliation, broader downloading and subsequent
data review remain pending at this snapshot. No inference, quality result,
promotion or training change. The full restoration goal remains active.
