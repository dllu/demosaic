# Preserve evaluation disk reserve by consolidating identical checkpoint snapshots

Recorded: 2026-10-23T18:17:35-07:00 (America/Los_Angeles).

Consolidated byte-identical, immutable evaluation checkpoint snapshots to
maintain space for the queued quality evaluations and complete GFX exports.
Seventeen checkpoint hashes had 61 distinct read-only input files;
replacing 208 owned snapshot aliases with hard links removes 18.825 GiB of
duplicate allocation while preserving every original path and file byte.
External free space rises from about 267.46 to 286.29 GiB; future evaluators
retain their existing 256 GiB starting reserve. Concurrent training can affect
the filesystem free-space delta.

Hashed every distinct input before any replacement and rehashed each canonical
file afterward. An independent postcheck verifies all aliases, link counts,
sizes, modes and owners. Excluded both current V102/V104 digests, all inodes
referenced by active plans, writable files, nonregular files and inodes with
unknown aliases. No source photographs, datasets, model values, live training
checkpoints or evaluation recipes change. Current core/optional-export hashes
and all active frozen plan/source bindings remain exact; five owned process
handles remain live.

The initial inventory driver stopped before any plan or mutation because a
matching filename was writable. Preserved that driver and recorded the reason;
the corrected driver explicitly skips writable files before constructing the
immutable plan. Content verification completed before the first replacement.
[Execution and independent postcheck](../docs/results/checkpoint-storage-consolidation-20261023-v1.json).
