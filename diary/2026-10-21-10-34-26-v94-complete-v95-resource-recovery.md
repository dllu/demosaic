# Complete V94 and recover V95 after restoring system disk space

Recorded: 2026-10-21T10:34:26-07:00 (America/Los_Angeles).

On revalidating the actual original job, V94 has completed its full20k stage
and V95 has failed around logged step1,025. The original controller stopped its
own worker at the unchanged resource floor; its preserved error is
`AssertionError('Training resource floor')`, recorded locally at
2026-10-21T03:30:45.274626-07:00. Original controller/worker identities are exited.
The failed V95 trial has no saved training checkpoint and no validation event.
Its metric rows remain finite; this is a resource stop, not a numerical failure.

The actual V94 independent CPU-only audit passes all four diagnostics, final20k
and separate validation-best: source/lineage/effective architecture, 71 finite
model/71 EMA tensors,69 finite Adam states with each file's correct counter,
curated/native/paired/validation/protocol identities,801 scheduled metric rows,
five scheduled validations and exact first24 input replay against its discarded
CUDA probe. V94 executes20k training forwards,160 validation forwards and20,160
DINO calls. Its final EMA container SHA256 is
`7fbb24691c10b9ba23881aee264e61165a189e7f704a54e622b30edab160251f`.
Validation-best is at12k; final20k remains primary. Independent audit receipt:
`b82770b8cdd0bfb9ffd38b577c83dd5d07decb7cbf658e7a34bbbb66ede54db5`.
Across all801 logged batches, V93/V94 preserve390 shared native/paired batches
and change411 Commons batches. No trained-model quality claim follows from
these engineering checks.

The system disk initially has only about50 GiB free, below the original64 GiB
reserve; external storage has about495 GiB. Reclaim space through this project's
own cold experiment checkpoints, preserving originals and other workloads.
The first metadata screen found only one single-link read-only candidate, so
broaden the inventory to closed owned checkpoint inodes with every alias found
under the project cache. Check that no other project Python owner is active,
exclude every current-study input, and verify all selected source hashes.

Relocate66 cold checkpoint inodes/116 aliases,32.4023 GiB allocated, to the fresh
owned external namespace
`/mnt/external/demosaic/cold-project-checkpoints-20261021-v1/`.
Each external copy passes whole SHA256, mode and nanosecond-mtime checks before
atomic replacement of its original path by a symbolic alias. All aliases of
each old inode share one verified external target. Original paths and checkpoint
bytes remain accessible; physical inode/link changes are explicitly recorded.
No original photo, source code, current study input or historical receipt is
changed. Current frozen source/input guards still pass. The system disk returns
to about81.6 GiB free and the external SSD retains about462.2 GiB. Relocation
receipt: `edd4d2db1f3712b666ac9d2d9256c8134aac0f5003ee544e79220f7ecdd3b0c5`.

Added `scripts/recover_v43_quality_trial.py` for this explicit manual early-V95
recovery. It verifies the terminal failed owners, all six passed preflights,
completed controls, matched input traces and restored resources, then preserves
all62 failed-trial files with byte hashes/path mapping. The unsaved external
trial is archived at
`/mnt/external/demosaic/v43-curated-training-20261020-v1/failed-train-V95-before-manual-recovery-v1/`;
old status, claim and log evidence are retained. The original completed V93/V94,
frozen training plan, worker code, configuration, initializer, precision,
20k schedule and all resource bounds remain unchanged. Only V95 starts fresh
from the original V43 step2000 EMA; no partial learned state is reused.

Recovery plan at `.cache/quality-first-20261020/V95-manual-recovery-v1/`:
`db1f5cc39a1ce3f0a719f3063fa1284119637d49a91ed15934ed7687f9caabf2`.
Actual recovery controller PID3351332/create1792603701.53 and new V95 worker
PID3351636/create1792603763.29 are live. The original study's `status.json`
tracks the new identities and retains recovery provenance. Both original and
recovery input/code guards pass. The original single-attempt controller claim
remains historical; this is a diagnosed explicit restart, with no automatic
retries. The new controller still requires stable48 GiB RAM for60s, active24 GiB
RAM, root64/external384 GiB reserves, the original CUDA cap and stage runtime
bound. Final completion additionally requires all three full training traces
to pass their matched-domain comparisons.

At the recovery receipt snapshot, new training has progressed through logged
step1,275. All42 scheduled recorded batch fingerprints through the archived
step1,025 prefix exactly match, with finite new recorded losses/gradients.
This is not a claim that unlogged intermediate batches or floating-point
training states are bit-identical. Prefix replay receipt:
`7a591dd9e1bbf222116f68aad9f0c09c369ab4e143076dc4ff05546c8b03a64b`.

[Completed V94 audit](../docs/results/v43-quality-V94-completed-training-v1.json),
[storage relocation](../docs/results/cold-checkpoint-relocation-20261021-v1.json)
and [actual V95 recovery](../docs/results/v43-quality-V95-manual-recovery-v1.json)
retain the evidence. Ruff and actual preparation/start/replayed-input integration
checks pass for the new recovery tool. Updated quality/validation/experiment/
completion guides. V95 still needs its complete20k endpoint, then the full
matched photographic/real/weak-detail/color/GFX evaluation and actual native
crop review. V43 remains the working reference; speed work stays deferred.

