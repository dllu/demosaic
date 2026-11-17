# Second ordinary-photo pass verified

Recorded: 2026-11-17T14:18:00-08:00 (America/Los_Angeles).

The original 100k trajectory completes its second ordinary
photo epoch at update 33,985. The 34k checkpoint write completes.
The audit checks 544,000 slots and 136 conditioning chunks.
There are 181,674 ordinary visits, 9,479 reviewed visits,
90,660 sources with two ordinary visits and 118 with three.
The original 30k log prefixes and 120 chunks remain exact.

The second visit changes the cached rectangle for 90,757 of
90,778 sources. Median intersection over union is 0.634 and
926 pairs have disjoint rectangles. This is crop coverage
before geometric augmentation. The 50k native review stays
queued on the immutable checkpoint.
[Training status and verified audit](../docs/full-corpus-scaling.md#second-ordinary-photo-pass).
