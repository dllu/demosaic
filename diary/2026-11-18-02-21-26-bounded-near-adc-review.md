# Bounded near-ADC correction and 100k review queue

Recorded: 2026-11-18T02:21:26-08:00 (America/Los_Angeles).


The complete 16-source faint panel confirms the low-noise crossover.
At the smallest prior the single residual lift lowers 86k weakest-band
RMS from 2.953 to 2.382 DN16 on 12 of 13 eligible sources. Every
eligible source regresses with the single lift at each of the
three higher priors.

The 12-photo comparison excluded the first four viewed sources.
On that prospective subset, the bounded lift lowers 86k weakest-band
RMS from 2.744 to 2.360 DN16, with nine of ten eligible sources
improving. Zero conditioning on the same sensor inputs reaches
2.434. In the four-color reserved palette the bounded correction
lowers the worst bias from 19,449 to 105 DN16 and worst centered RMS
from 2,217 to 87 DN16. The intermediate-noise 6,703 DN16 bias
remains when the guard declines the correction.

The changed read-family coordinate partially explains the yellow
failure. The training ledger has no read-electron ratio above 7.53.
Both small and intermediate diagnostic ratios exceed 31. Feature
clipping leaves large errors, and the ADC-family-only substitution
raises intermediate GBRG bias to 9,428 DN16.

The new opt-in helper matches the scored prototype on all 48 active
batches and bypasses 146 other predictions by identity, including
18 standing GFX predictions. The 111-test focused suite passes.
Two prior offline waiters exited before scoring. Both tables were
regenerated from the completed prediction receipts, with no
additional model calls. The native boards and exact triplet subsets
have been viewed.

The original long run is above 97,000 updates. Its live observer
verifies 110 native input cases and their 220 existing V120 and 86k
predictions. A separate adoption trial rebinds 54 existing camera
batches with the same CPU forwards and metric source. The observer
now waits for the real 100k endpoint before launching numerical
reviews. The current history has no 100k measurement.

[Completed near-ADC report](../docs/noisy-cfa-residual.md) ·
[100k review queue](../docs/results/full-corpus-long100k-review-queue-v1/publication.json) ·
[Main standing GFX](../docs/gfx-qualitative.md) ·
[Fine cab GFX](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
