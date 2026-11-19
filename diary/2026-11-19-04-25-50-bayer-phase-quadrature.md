# Measure Bayer phase from disjoint donors

Recorded: 2026-11-19T04:25:50-08:00 (America/Los_Angeles).

The fixed eight-donor reconstruction still has phase error. Adding a
quarter of the exact perpendicular correction reduces ISO6400 intact
planted-wire RMS by 6.78 DN16. Both local greens measure too little of
that correction reliably, and all local gains calibrate to zero. A
phase estimate checked across disjoint cardinal and diagonal donors
recovers 1.23 response points and reduces intact and true-gap RMS by
2.58 and 1.88 DN16. On 48 natural backgrounds at ISO6400 the same dose
adds 0.894 DN16 of flat RMS and loses 0.153 fine-response points.
[Results and native comparisons](../docs/bayer-phase-quadrature.md).

I viewed three exact-target native comparisons and both standing GFX
families. The overcast sky stays smooth. Both fine cab ROIs retain
mottling and incomplete junctions under both priors. This study reused
the frozen EMA reconstruction and calibrated scalar gains. It adds no
eligible endpoint to the broad PSNR history. Eleven focused tests pass.
[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Performance history](../docs/performance-history.md).

Both full-epoch training traces match through 29,500 and 30,000 updates.
At 30k each arm has 60,000 distinct photos and 240,000 native queries.
The 30k exact-photo review started and its standing review follows it.
The last complete numerical and native evaluation is the matched 25k pair.
[29,500 audit](../docs/results/scene-full-epoch-v1/paired-prefix-029500.json) ·
[30,000 audit](../docs/results/scene-full-epoch-v1/paired-prefix-030000.json) ·
[25k quality review](../docs/scene-full-epoch-25k.md).

The local-only continuation reached 30,500 verified updates, 61,000
distinct photos and 244,000 native queries.
[Local audit](../docs/results/scene-full-epoch-v1/local-030500-prefix.json).
