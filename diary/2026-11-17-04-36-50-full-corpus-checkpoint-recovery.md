# Recover a stalled best-checkpoint write without replaying training

Recorded: 2026-11-17T04:36:50-08:00 (America/Los_Angeles).

After publishing [the completed64-source study](../docs/whole-scene-context-development64.md)
and primary admission in161a505f, a final health check found a live but stalled
control worker. The preceding diary's running status described process liveness,
not verified new optimizer progress. The next health checks must include recent
step/file progress as well as PID and creation-time ownership.

The [recovery report](../docs/full-corpus-checkpoint-recovery.md) preserves a
verified>1h stall with `best.tmp` open and no checkpoint/log/source progress,
despite CPU spin. OS denied debugger attachment, so exact CUDA/C++ cause is
unknown. Retained the valid complete6k checkpoint, older best and partial bytes;
verified all91 raw/EMA tensors and89 Adam steps plus RNG. Stopped only exact
ownedPID1200382/create1794910101.73 with SIGTERM; no SIGKILL required. The original
controller recorded−15 and stopped. Other processes/primary evaluation untouched.

Avoid the redundant best-state serialization by atomic hardlink retention of
completed last. Later last replacement preserves best; stale retention
temporaries fail explicitly. Two tests,20 existing training/checkpoint regression
tests and an actual6k-file qualification pass.
All remaining training source bytes reproduce the old frozen trainer exactly.
The unchanged6k raw/EMA/Adam/RNG/global indices resume at6001, with the same20k
horizon, B16, source order, data/noise/loss/EMA/optimizer policy. The long arm
keeps its original complete1k state and100k horizon, continuing afterward.

The published progress snapshot confirms actual updates6001→6350, beyond mere
PID liveness. First100 resumed source rows continue global draw starts96000
through97584 after original prefix95984. Initial load/frozen-DINO guards pass
before these learned updates. The new worker subsequently continues advancing;
do not label this observation as a completed training phase or next checkpoint.

Preserve all admission failures: v3 preparer compares receipt/checkpoint identities
incorrectly and stops on CPU; v4 worker hits the frozen output-root guard; v5
lacks pyproject/lock/license metadata required by source capture. Both worker
failures precede model construction and optimizer updates. Correct v6 includes
the full metadata and moves outputs within its frozen root, with only `run`
changed in training configs. Bind adopted state to immutable checkpoints,
so finishing control cannot invalidate long-arm admission.

The failed prefix never wrote its terminal aggregate summary; do not invent it.
Its original controller wall time8412.536 seconds includes the stall. Closed
source/crop/conditioning records and checkpoint identities remain available;
resumed timing and actual learned progress are separately recorded.
Neither scaling horizon is complete. Broad scores, both fence reviews and
native GT triplets remain required for completed scaling endpoints.
The [PSNR history](../docs/performance-history.md) stays through V131.
