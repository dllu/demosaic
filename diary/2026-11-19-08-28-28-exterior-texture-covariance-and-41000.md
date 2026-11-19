# Exterior texture covariance and 82,000 matched photos

Recorded: 2026-11-19T08:28:28-08:00 (America/Los_Angeles).


The exterior covariance uses measured disjoint near RAW texture
patches to weight local coefficients without borrowing the donor
phase. On 48 held-out natural photos the full-strength ISO6400 lift
adds 0.655 response points and raises fine-increment RMS 1.673 DN16
and flat RMS 3.097 DN16. Equal directional power has almost the
same response at matched added quiet RMS. A stricter lift of the whole
parent pattern recovers very little new detail.

Swapping these corrections across independently generated capture
groups of the same scene keeps correction energy fixed and reduces
excess fine error by 0.596 DN16. The full correction still increases
error by 0.227 DN16 in the swapped composition. Both exact-target
triplets and both GFX scene families were viewed. Fine cab junctions
remain incomplete.
[Report, repeat test and crops](../docs/scene-raw-covariance.md) ·
[Main scene review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md).

Matched training verifies 41,000 updates on 82,000 distinct photos
and 328,000 queries per arm. The local-only continuation verifies
85,000 photos. The matched 40k review remains the latest complete
photo and standing evaluation. This covariance replay uses the same
frozen 100k EMA and adds no fixed photo or measured-camera scores.
[Matched 41k audit](../docs/results/scene-full-epoch-v1/paired-prefix-041000.json) ·
[Latest matched quality review](../docs/scene-full-epoch-40k.md) ·
[Comparable PSNR history](../docs/performance-history.md).
