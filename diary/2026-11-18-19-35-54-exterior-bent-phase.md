# Transport exterior bent phase and check neighboring frequencies

Recorded: 2026-11-18T19:35:54-08:00 (America/Los_Angeles).

The exact-geometry replay detects 13/16 earlier occluded draws
using one Bayer quarter and 16/16 using three when the phase is
estimated in the exterior. The initial tile searches still miss the
correct high-frequency direction. Unbending the wide exterior
spectra gives 20/24 correct pairs on 12 new occluded fields.

The neighboring-frequency check retains 11 new correct pairs and
raises intact response from 39.87% to 50.32% over the wide fit.
Increment error falls 3.75 DN16. Two stronger-only controls still
receive new corrections, and unrelated gaps have 1.84 DN16 more
added texture. Flats are unchanged. The earlier pooled proposal
adds faint modulation to the building. The adjacent-frequency
comparison rejects it and reproduces the wide standing views.
[Numeric study and exact crops](../docs/query-exterior-witness.md) ·
[Standing main and cab comparisons](../docs/query-exterior-witness.md#standing-gfx100s-comparisons).

The first three new 500-update segments match between the local and
spatial training arms. This verifies 6,500 updates, 13,000 distinct
photos and 52,000 queries per arm on the original schedule. The
latest complete numerical and native quality comparison is 5,000.
[Matched prefix](../docs/results/scene-full-epoch-v1/paired-prefix-006500.json) ·
[Comparable PSNR coverage](../docs/performance-history.md).

The additional 36-photo validation uses the frozen thresholds and scale.
It replicates the occluded gain at 9.55 points, lowers increment error
by 2.49 DN16, and increases added luma in unrelated gaps by 3.96 DN16.
[Replication protocol](../docs/results/query-exterior-witness-v1/replication-preregistered.json).

[Completed replication and images](../docs/query-exterior-witness.md#prespecified-36-photo-replication).
[Subsequent 7,000 matched input audit](../docs/results/scene-full-epoch-v1/paired-prefix-007000.json).
