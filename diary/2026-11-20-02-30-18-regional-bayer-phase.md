# Limit Bayer color phase to locally aligned strands

Recorded: 2026-11-20T02:30:18-08:00 (America/Los_Angeles).

Keep the crop-wide color power screen, then weight the red and blue
observations by signed chroma-to-green phase agreement across their
3 × 3 node neighborhoods. The 32 × 43 pixel semiaxis reversal's
phase correlation recovers from 0.95097 to 0.98345. After held-green
acceptance its extra green error falls from 0.99 to 0.07 DN16
relative to green-only. The neutral delivery still has higher RGB
error than the synthetic parent on the opposite-color patch.

On 24 fresh Commons backgrounds and two draws, the regional fit gains
0.504 warped and 0.068 straight weak-response points over green-only.
Flat and uniform scores stay equal. Opening the direction ranking adds
0.413 DN16 in one edge-only draw. Both standing GFX families were
viewed at native pixels. The sky stays smooth and fine cab crossings
remain incomplete.

Packaged the opt-in crop method as `pooled-color`. All 488 crops
match the original replay bit for bit. The median one-thread CPU
fit takes 39 ms on the right cab and 47–49 ms on the left.

[Report and timings](../docs/cfa-regional-phase.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).
