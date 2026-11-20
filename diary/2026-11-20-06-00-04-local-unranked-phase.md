# Check both Bayer directions when wire rank disagrees

Recorded: 2026-11-20T06:00:04-08:00 (America/Los_Angeles).

The [independent direction replay](../docs/local-unranked-phase.md) checks
the two nominated wires separately when the green lattices disagree on
rank. The locked outer collar gains 0.863 second-direction contrast
points on 32 new sources and lowers intact error by 1.366 DN16. The
12 ambiguous draws gain 4.595 points at the median.

The calibration never activated the alternate path on an exact gap.
The new panel exceeds its total added-gap and quiet budgets. Of the
1.575 DN16 total gap change, 1.561 is attributable to the continuing
direction. Exact gap luma error falls slightly. The weaker, absent
direction still adds 0.112 DN16 mean luma and one flat-core draw acquires
1.013 DN16. The tested fallback remains a research replay.

Both [fine cab profiles](../docs/gfx-green-mesh.md) change subtly in
their left crop, with crossings still incomplete. The [main scene](../docs/gfx-qualitative.md)
retains the smooth sky and connected coarse crossings. Both
native exact triplets and all 12 standing boards were reviewed.

The parents use frozen EMA weights and the broad benchmarks in the
[PSNR history](../docs/performance-history.md) fall outside this replay.
[Source and receipt bindings](../docs/results/local-unranked-phase-v1/publication.json).
