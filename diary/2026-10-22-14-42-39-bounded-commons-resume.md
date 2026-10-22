# Bounded Commons download resumes while quality comparisons run

Recorded: 2026-10-22T14:42:39-07:00 (America/Los_Angeles).


Resumed the explicitly authorized background Commons download while V101 and
its existing quality queues continue. The archive was partial, despite completion
of its previous bounded batch: 178,117 downloaded originals, 279,548 pending.
The next4,000 originals total27.66GiB by publisher metadata;3,912 meet the current
native-crop size requirement and their two-scale caches estimate24.47GiB more.

The new singleton controller uses the unchanged copied downloader, two workers,
.25 starts/second,336GiB reserve,4,000-completion cap and12h deadline, nice10/idle
I/O. The shared lock survives in the child. Frozen code hashes pass; no discovery,
enrichment, preparation or training admission occurs. At14:42PDT both exact
owners were alive and162 new originals had been published. Final independent
size/SHA1 auditing waits for termination. The four existing active plans pass
their guards and do not bind the mutable live archive index.

Published the bounded launch/capacity receipt and rewrote `docs/commons-download.md`
around the current workflow, retaining links to historical machine receipts.
This does not claim the new data improves a model. V100/V101 retain their frozen
88,484-source cohort; arrivals require a later prepared, screened and reviewed
freeze. No originals, other project files or active snapshots were modified.
