# Full-corpus training: checkpoint-write recovery

The20k control stopped advancing after its completed step6,000 checkpoint.
The worker remained alive and consumed CPU for over an hour while its open
`best.tmp` stayed at131,685,248 bytes. Training/source logs and the complete
checkpoint did not change. This was a verified checkpoint-write stall; the
exact CUDA/C++ cause is unknown because the OS denied debugger attachment.

The exact owned worker was terminated with SIGTERM after retaining its complete
state and partial output. No other process was stopped. The original controller
then recorded return code−15 and stopped; it did not silently retry.
[Exact diagnostic, failure, admission and resume evidence](results/full-corpus-checkpoint-recovery-v1/publication.json).
[Independent state/source/progress audit](results/full-corpus-checkpoint-recovery-v1/independent-review.json).

## Preserved state and minimal fix

The complete6k checkpoint SHA256 is
`e9c8745bf3a877c2e32608cf9972741676a1e64558af42622aa66a1894840721`.
It loads with91 raw and91 EMA tensors,89 finite Adam states all at step6,000,
and Python/CPU/CUDA RNG. The20k horizon, B16 and source-epoch configuration are
unchanged. The long100k trajectory remains at its original complete1k state,
SHA256 `e72da50252f1de4c76ecf7985d940d4094a6e8b7de0dca50269cc39eb0ba8c54`.

[train.py](../src/demosaic/train.py) now retains the already-complete `last.pt`
as `best.pt` using an atomic hardlink, avoiding a redundant serialization of
the same GPU state. Later saves atomically replace `last.pt`, so the retained
best inode stays fixed. A stale retention temporary is an explicit error.
These files must share a filesystem, as they do within each run directory.
No model, loss, optimizer, EMA, sampler, corruption or schedule math changes.

Two tests check complete state/RNG retention across later last-file replacement
and preservation of existing bytes on a stale temporary. Twenty existing
training/checkpoint regression tests also pass, including uninterrupted-versus-
resumed model/optimizer/EMA/RNG comparisons. A separate qualification
uses the actual503MiB6k checkpoint and verifies its retained best stays exact
after replacement of a probe last file. The probe6001 dictionary is an IO
fixture, not a learned update. Removing just the helper/import/call substitution
reproduces the original frozen training source byte for byte.

## Explicit continuation

The admitted allocation continues **6,001→20,000**, then **1,001→100,000** on
the long arm. It adopts raw/EMA/Adam/RNG and global source counters; no prefix
is replayed and neither horizon is reset. Each stage verifies its saved starting
identity before launch. Resume outputs live under the new frozen checkout's
permitted output directory; all training configuration values except that
output location match the originals. Original checkpoints, failure directories,
logs and source snapshots remain intact.

At the published observation cutoff, actual optimizer logs advance from6,001
through6,350. The first100 resumed source rows have global draw starts96,000
through97,584, immediately after the original prefix's95,984. Startup declares
90,778 sources and the original20k horizon. This verifies real resumed progress,
with source indices continuing after6,000 B16 batches; it does not claim the
next full checkpoint, endpoint evaluation or productive full-run duration.

Admission failures are preserved separately. The first preparer compared a
completion-receipt hash with a checkpoint hash and stopped on CPU. A later
worker was correctly rejected by the frozen checkout's output-path guard; the
next lacked dependency/license metadata needed by source capture. Both stopped
before model construction or optimizer updates. The corrected v6 admission
includes the complete metadata and a permitted output location. This is an
explicitly reviewed recovery, with no automatic retry loop.

The original failed prefix's terminal summary and in-memory aggregate counters
were never written. They are not reconstructed as original receipts. Complete
source/crop rows and conditioning chunks remain available, alongside the6k
state and closed logs; publication binds the lost-summary limitation explicitly.
The original controller's8,412.536-second elapsed phase includes the stall and
is not productive training time. The resumed phase measures its own duration.

The CPU [whole-scene primary benchmark](whole-scene-context-primary-admission.md)
continues independently. This repair adds no quality measurement or history
point. Scaling endpoints still need full427/known-unseen scores, actual native
triplets and both protected fence reviews. [Training recipe and coverage](full-corpus-scaling.md).
