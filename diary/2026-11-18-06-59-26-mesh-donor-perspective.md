# Test exterior perspective and gap support for weak mesh

Recorded: 2026-11-18T06:59:26-08:00 (America/Los_Angeles).

Replayed 48 fixed present/absent pairs. The original center check
accepts 1/12 ISO400 broken-wire pairs. Exact projected geometry accepts
12/12 and geometry measured across disjoint exterior donor tiles accepts
8/12. A separate color diagnostic improves high-noise prediction when
given exact geometry. Nearly all of that gain disappears with measured
geometry. No new checkpoint was trained.

On 24 fresh pairs, the shorter support reduces added gap texture from
3.34 to 0.16 DN16 RMS at similar ISO400 broken-wire response. It attenuates
continuous mesh. No ISO6400 or matched negative-control role changes.
The wider cached GFX review finds 21 extra donor tiles for the coarse
fence and none for the fine cab. Short support fades the left lattice.
All eight standing camera boards and six synthetic comparison boards
were viewed at native size. [Report](../docs/local-mesh-projective.md) ·
[Main scene](../docs/gfx-qualitative.md) · [Fine cab](../docs/gfx-green-mesh.md).

The component has scoped numerical and native evidence. The fixed broad
panels for the 100k and matched 12k endpoints were still collecting.
[Primary history](../docs/performance-history.md).
