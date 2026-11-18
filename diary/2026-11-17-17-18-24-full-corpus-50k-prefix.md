# The full-corpus run reaches 50,000 updates

Recorded: 2026-11-17T17:18:24-08:00 (America/Los_Angeles).

The full-corpus continuation saved 50k on its original 100k learning-rate
horizon. The state contains 91 raw and 91 EMA tensors, 89 Adam states at
step 50,000 and all three RNG fields. The source audit checks 800,000 target
slots and 200 conditioning chunks. It finds 266,909 ordinary draws from
all 90,778 sources. Of those sources, 85,353 have reached their third visit.

Across those 85,353 sources, median cache coverage grows 54.4% → 69.1% →
76.7% across three crop visits. The median third visit adds 5.0% of the
cache field. The new CPU review is processing the immutable 50k EMA on
the same 110 inputs as V120 and long 20k. Its results and native viewing
are separate from this checkpoint and coverage audit.

[Training and source coverage](../docs/full-corpus-scaling.md#long-schedule-50k-milestone) ·
[Saved-state provenance](../docs/results/full-corpus-long50k-prefix-v1/publication.json).
