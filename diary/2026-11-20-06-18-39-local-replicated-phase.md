# Limit replicated Bayer phase to its verified station

Recorded: 2026-11-20T06:18:39-08:00 (America/Los_Angeles).

The [replicated phase report](../docs/local-replicated-phase.md) tests
direction-balanced fixtures before drawing sensor noise. The first two
panels favor a two-green check with support in the next station along
the wire. Its third-panel trial adds 0.280 DN16 mean luma from the missing
direction. Nearly 99 percent of that addition's energy lies within eight
pixels of the exact gap boundary.

The station cap prevents adjacent station strengths from spreading
across a weakly supported station. On a fourth group of 24 new sources,
the locked cap gains 1.084 second-direction response points over nearby
phase and lowers intact error by 2.089 DN16. At matched response, added
missing-direction luma goes from 0.090 to 0.034 DN16. The added flat-core
peak is 0.112 DN16. Edge and uniform controls reproduce nearby phase.

The opt-in crop mode reproduces the replay exactly on all 288 synthetic
and eight standing crops. Both fine [cab review](../docs/gfx-green-mesh.md)
profiles barely change on the left and still have incomplete crossings.
The [main scene](../docs/gfx-qualitative.md) retains smooth sky and coarse
crossings. Both exact-target triplets and all 12 standing boards were
viewed.

The [scoped tradeoff plot](../docs/assets/local-replicated-phase-v1/station-gap-tradeoff.png)
measures a frozen-weight crop component. The fixed broad panels in the
[PSNR history](../docs/performance-history.md) fall outside this replay.
[Receipts and source bindings](../docs/results/local-replicated-phase-v1/publication.json).
