# Stabilize weak mesh fits across crop origins

Recorded: 2026-11-18T06:18:44-08:00 (America/Los_Angeles).

Moved the mesh fitting query by up to 16 native pixels with the output ROI
and neural parent held fixed. Recomputing the exterior pair dropped coarse
fence support for three of 13 placements. Holding the pair fixed and anchoring
the Bayer reserves to sensor columns raised the worst left-cab correction
similarity from 0.796/0.774 to 0.884/0.893 under the two priors. The overlap
median preserved the left lattice and removed sparse foliage corrections.
All eight standing boards were viewed at native size, including both cab
JPEG references. [Main scene](../docs/gfx-qualitative.md) ·
[Fine cab](../docs/gfx-green-mesh.md).

The fresh 48-pair panel showed a gain on ISO400 occluded wires, with 76.32%
weak response and 32.05 DN16 increment RMS from 31.02% and 43.70 DN16. One
broken wire gained 4.51 DN16 RMS inside a known gap. All 24 ISO6400 pairs
retained their parents. The optional crop helper reproduces all eight archived
camera outputs bit for bit. [Report and executed evidence](../docs/local-mesh-stability.md).

This is component inference using the existing 2k checkpoints. The scoped
numerical and native reviews are complete. The comparative PSNR history
covers independently evaluated broad endpoints.
[PSNR history](../docs/performance-history.md).
