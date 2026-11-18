# Train and review paired luminance detail

Recorded: 2026-11-18T14:28:59-08:00 (America/Los_Angeles).

Completed both luminance heads over frozen Corpus 100k EMA. The run used
1,200 updates and 7,200 native examples per head from 2,400 distinct
photos and took 1,241.59 seconds. The final checkpoint holds raw and EMA
weights for both heads. Evaluation uses EMA and binds checkpoint SHA256
`02f8d5e6664bd580bafe2abeb3b8584b070b60bfadfefaff587cadd8bd643d7f`.

The 64-photo numerical review is complete. At ISO6400 the paired
head with both support windows gains 0.47 percentage points of
aligned response. Fine-increment RMS falls 1.09 DN16 with coupled
noise and rises 0.31 DN16 with independent noise. The shorter support
test lowers excess flat variation against a wider guard matched
for delivered correction RMS. The actual image review covers three
synthetic comparisons with exact-target triplets and eight GFX boards.
The sky stays smooth and fine cab crossings remain incomplete.
[Report and signed-response sweep](../docs/paired-luminance-detail.md) ·
[Main GFX100S review](../docs/gfx-qualitative.md) ·
[Cab mesh review](../docs/gfx-green-mesh.md).

The full-photo and measured-CFA history retains the independently
evaluated parent checkpoint. This scoped head contributes its own
64-photo increment metrics. [PSNR history](../docs/performance-history.md) ·
[Publication receipt](../docs/results/paired-luminance-detail-v1/publication.json).
