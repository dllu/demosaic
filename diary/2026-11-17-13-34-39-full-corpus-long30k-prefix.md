# Verified source and crop coverage at 30k

Recorded: 2026-11-17T13:34:39-08:00 (America/Los_Angeles).

The original long cosine schedule reaches 30,000 updates and
480,000 target slots. All 90,778 ordinary photo sources appear.
There are 160,479 ordinary and 8,383 reviewed-region visits.
The source audit checks each step's data seed and ordinary
epoch index, plus the dimensions and finite values of all 120
conditioning chunks. The first 20,000 step rows are a bit-exact
match to the prior immutable prefix.

Of 69,701 sources seen twice in the ordinary stream, 69,688 use
different cached crop rectangles on their second visit and 694
have disjoint rectangles. Median intersection over union is 0.634.
That describes cached rectangles before geometry augmentation.
The 30k checkpoint write is logged. The next immutable checkpoint
review waits for the 50k state.
[Scaling status and independent prefix audit](../docs/full-corpus-scaling.md#observed-source-and-crop-coverage-through-30k).

A separate confirmation of the weighted phase refit is running on
fresh procedural geometries and RAW noise. Thresholds and scales
come solely from the previous development panel. Seven of 32 batches
had closed at this entry.
