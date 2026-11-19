# Confirm band-limited regional mixing on a separate photo cohort

Recorded: 2026-11-19T09:45:09-08:00 (America/Los_Angeles).

Low-passed the signed luminance boost after multiplying by the spatial
gate, with a rolloff from 0.24 to 0.32 cycles per native pixel. The
refit treats each calibration noise/draw group separately for fine
response and upper-band error. On the 48 fixed ISO6400 independent
sources, fine-flat RMS falls 0.421 DN16 and upper-flat RMS falls
0.038 DN16 versus Corpus 100k. Fine-increment RMS falls 0.043 DN16.
The separate 32-photo cohort gives fine-flat and upper-flat gains of
0.186 and 0.025 DN16. Its fine response changes −0.017 points.
Coupled ISO6400 and independent ISO400 retain small increment costs.

Verified direct output on all 192 fixed test groups, viewed four
exact-target triplets, and viewed both standing fence families with
the original coordinates and display. Multiple crossings remain
missing in the fine cab. The composition requires both learned EMAs.
Broad continuation reviews are still queued at 50k.
[Refit report](../docs/scene-mixture-upper-band.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine cab](../docs/gfx-green-mesh.md) ·
[Performance history](../docs/performance-history.md).

Matched inputs now verify through 45,000 updates on 90,000 photos per
arm. The latest completed matched quality review remains 40k.
[Paired audit](../docs/results/scene-full-epoch-v1/paired-prefix-045000.json) ·
[40k quality review](../docs/scene-full-epoch-40k.md).
