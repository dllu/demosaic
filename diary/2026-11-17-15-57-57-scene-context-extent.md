# Local and distant preview context with fixed RAW tiles

Recorded: 2026-11-17T15:57:57-08:00 (America/Los_Angeles).

I kept the spatial 2k EMA checkpoint and all native RAW tile inputs fixed.
Blurring the distant part of its scene preview changed the real foliage
and coarse fence by 4.14 and 5.15 DN16 RMS, and the overcast sky by 0.45.
Blurring the near region changed the two exact-target development sources
about four times as much as blurring distant context. Full context shows no
consistent weak-band error benefit. The sky remains smooth, and thin canopy
cords and cab crossings remain incomplete.

All ten full-context predictions replay bit-for-bit. The independent audit
reproduces 336 reductions and 72 retained display cells. All 16 native boards
were viewed. This is an inference intervention on an existing checkpoint.
Training and the standard full427 benchmarks continue separately.
[Context report](../docs/scene-context-extent.md) ·
[Main GFX comparison](../docs/gfx-qualitative.md) ·
[Cab comparison](../docs/gfx-green-mesh.md) ·
[Primary history](../docs/performance-history.md).
