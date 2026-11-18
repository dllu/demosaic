# Adjacent RAW donors recover right cab crossings

Recorded: 2026-11-18T08:19:31-08:00 (America/Los_Angeles).

The right cab's standard donor grid selects a different pair of peaks.
The adjacent tile supplies the visible wire directions. Ranking its pairs on the reserved
quarter and validating on separate samples yields visible crossings
under both priors. The 13 placements support both directions. Ported
the experimental fallback to `refine_local_raw_mesh` and verified
bit-exact right result, both original options on all eight inputs,
and the combined gap option. The right reconstruction remains softer
and more regular than parts of the ISO100 reference.
[Crop API and native review](../docs/donor-phase-transport.md).

Exterior phase estimation substantially improves continuous ISO6400
synthetic wire response and reduces mean wire error. Gaps gain false
repeats, with partial repair from the existing gap audit. The fixed
phase transfer leaves every standing camera crop identical to its
earlier wide-donor result. Reviewed 16 GFX boards, five exact synthetic
comparisons and both continuous triplets. This component adds no
full-checkpoint PSNR points.
[Main GFX](../docs/gfx-qualitative.md) ·
[Fine cab mesh](../docs/gfx-green-mesh.md) ·
[Primary comparison history](../docs/performance-history.md).
