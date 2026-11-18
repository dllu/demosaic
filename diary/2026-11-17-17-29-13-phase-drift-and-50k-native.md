# Review phase drift and the full-corpus 50k checkpoint

Recorded: 2026-11-17T17:29:13-08:00 (America/Los_Angeles).

The guarded quadratic phase search lowers weak response at equal quiet
error on the fresh ISO400 panel. Far response falls 8.81% → 6.10%;
increment RMS rises 11.199 → 11.241 DN16. An exact-geometry follow-up
recovers more detail in the lower-noise far cases, which gives a reason
to test geometry from stronger RAW regions. Both standing fences
reproduce the planar fit on the fixed crops. I viewed all ten boards.
[Phase drift results](../docs/phase-drift.md).

The 50k native report completes all 110 inputs and 26 boards. Ordinary
and shadow sRGB means improve slightly over V120. Fine-band error rises
on all four faint materials, and the bright orange ADC check reaches
1,490 DN16 maximum channel-mean bias in BGGR. The fine cab crossings
remain incomplete. V120 stays the recommended model while training
continues on the original 100k horizon. The 50k report covers the
retained panel and both GFX scenes.
[50k checkpoint quality](../docs/full-corpus-long50k-native.md) ·
[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Standard PSNR history](../docs/performance-history.md).
