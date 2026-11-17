# Full-corpus training: CPU checkpoint snapshots

**The second checkpoint stall requires a stronger storage fix.** The earlier
[best-file retention repair](full-corpus-checkpoint-recovery.md) successfully
saved subsequent checkpoints through13k. At14k the worker again stopped
advancing, this time with the first `last.tmp` open at131,685,376 bytes.
For over30 minutes, training/source logs, completed states and partial bytes
were unchanged while the worker consumed CPU. Removing the duplicate best
serialization was useful but insufficient. The exact CUDA/C++ cause remains
unknown; no debugger or root-cause claim is inferred from file position.

The exact owned worker received SIGTERM after a complete13k state and previous
best were retained as immutable hardlinks. Its controller recorded−15 and
stopped. No other process, including the CPU primary collector, was stopped.
The original partial output, frozen source, closed logs and failed admission
probe remain preserved. The first stop script's path assertion failed before
sending a signal; its corrected successor performed the recorded stop.

[Exact diagnosis, qualification, admission and resumed progress](results/full-corpus-checkpoint-cpu-recovery-v1/publication.json).

## State and storage-only change

The adopted control13k checkpoint SHA256 is
`3810d5ba0387ab0e73d895f5081eeaca37f88dd1fb88bf562dce6bfbe02645d8`.
It has91 finite raw/91 EMA tensors,89 finite Adam states all at13k, and the
original Python/CPU/CUDA RNG, B16 and20k horizon. The long100k arm retains its
complete1k checkpoint
`e72da50252f1de4c76ecf7985d940d4094a6e8b7de0dca50269cc39eb0ba8c54`.

[train.py](../src/demosaic/train.py) now takes an owned CPU snapshot of every
nested tensor before `torch.save`. CUDA transfers finish before serialization;
CPU tensors are copied too, so the snapshot cannot alias later live state.
Checkpoint events identify snapshot start, completed model/EMA/optimizer/RNG
groups and final completion. A stale temporary is an explicit error. Completed
last files still become best by atomic hardlink; a final save already performed
at the checkpoint boundary is reused rather than serialized again.

Only checkpoint storage/progress and the redundant final write change. Replacing
that source section and final guard with their prior definitions reproduces
the previous frozen training file byte for byte. Model math, loss, precision,
optimizer, EMA, source/noise order and both learning-rate horizons are unchanged.
Original output trees are not edited; recovery uses its own frozen checkout.

All37 checkpoint/training/execution regression tests pass, including exact
uninterrupted-versus-resumed states and ownership of nested CPU snapshot
storage. A separate qualification moves the actual13k raw/EMA/Adam tensors to
CUDA, saves through the new CPU snapshot, reloads and compares every nested
state value to the retained original, twice. Both passes are exact, including
RNG/config and all serialized tensors being on CPU. This qualification performs
no model construction, learned forward, noise draw or optimizer update. It
qualifies state transport; production checkpoint completion is a separate check.

## Explicit continuation and limits

The admitted v7 allocation resumes **13,001→20,000**, then **1,001→100,000**.
The unserialized13,001–14,000 segment is recomputed from13k; it is not counted
as another1,000 distinct updates or new source draws. Raw/EMA/Adam/RNG/global
indices and original horizons are adopted without reset or quality-based stop.

Actual resumed optimizer logs advance beyond13,250. The first250 source rows
are identical to the abandoned segment, with global draw starts208,000–211,984.
All250×16×14 conditioning values, steps and domains match exactly too.
This demonstrates execution and replay continuity, not mere process liveness.
The publication records a precise observation cutoff; later progress is not
silently substituted into that receipt. The next production checkpoint and
completed20k/100k durations remain pending at that cutoff.

**Subsequent production check:** step14,000 has now saved in0.5304 seconds,
and training has advanced past14,125. The retained complete checkpoint SHA256
is `8259e05a5f381c6e4e1e5fa34f88f6075c480737331aa5aee8a9fea418c1e75d`.
All91 raw/91 EMA tensors and89 Adam states are finite, every Adam step is14k,
RNG is present and all serialized tensors are CPU. This validates the first
actual save after the repair; longer-run reliability still needs observation.
[Exact production addendum and source/log snapshot](results/full-corpus-checkpoint-cpu-recovery-v1/step14000-addendum.json).

The stopped v6 phase lasted7,299.382 seconds including the stall and abandoned
1,000 updates. It is not productive time through the adopted13k state. The
older v2 phase's8,412.536 seconds also include a stall. Original terminal worker
summaries were not written and are not reconstructed as original receipts.

The [10k quality review](full-corpus-control10k-review.md) is separately complete
and finds faint-detail regression despite larger source coverage. This storage
repair changes no quality scores, model recommendation or PSNR-history point.
[Training recipe and remaining evaluation](full-corpus-scaling.md).
