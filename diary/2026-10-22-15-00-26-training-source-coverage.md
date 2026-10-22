# Measure actual source coverage in the fixed training schedules

Recorded: 2026-10-22T15:00:26-07:00 (America/Los_Angeles).


Audited the exact frozen V100/V101 source schedule with the actual training
`domain_indices` and clean-reader seed/choice logic. Read the parent checkpoint
configuration through a CPU memory map to identify V84's actual original
84,867-source manifest. The active88,484 pool adds3,640 IDs and removes23; one
of the24 visual exclusions was already outside the original V84 pool.

At the full planned10k/B16 endpoint each arm has55,843 photographic Commons
draws. V100 schedules41,379 unique photo sources, including1,686 distinct newly
eligible sources across2,291 examples. V101 schedules39,838 unique photo sources,
including1,631 new IDs across2,168 examples. Its2,844 reviewed ROI draws replace
ordinary draws; ordinary-photo unique coverage is39,834. With-replacement
sampling is intentional, but the pool size is not exposure to every source.

In a separate CPU-only process, traced24 actual clean-reader file opens across
first/middle/last scheduled samples and reviewed-ROI samples. All source paths
match the deterministic audit, and all clean outputs are finite3×256×256FP32.
No denoiser, noise generator, optimizer, GPU or original HDD read was involved.
The V101 sample-kind and per-ROI counts independently reconcile with the
previous sampling/target report. Histograms sum to88,484 sources and55,843
photo examples per arm; all active plans' guards pass.

Published the source-coverage receipt and a compact table in the current
quality-training guide. This is accounting for the full scheduled endpoint,
not a claim of completed active-trainer consumption or of a data-only quality
gain. Both10k budgets remain fixed. These counts will help choose a later budget
after quality results, rather than treating a larger pool as fully consumed.
