# V95 palette primary panels and PSNR history

Recorded: 2026-10-21T19:26:52-07:00 (America/Los_Angeles).

All three V43/V95/V96/V97 primary panels completed and their workers exited.
The fresh FP32 photo means are 34.89933 / 35.29553 / 35.27828 / 35.28321 dB;
known-camera means are 54.23334 / 54.33307 / 54.32564 / 54.32529, and unseen
means are 53.80629 / 53.76990 / 53.76643 / 53.76365. V97 minus matched V96 is
photo +0.00492 dB, paired-source 95% interval [−0.01276,+0.02189]. Neither new
endpoint establishes a photographic PSNR gain over V95.

The completed-panel operator independently reran coverage, arithmetic and
paired source-bootstrap checks on 111,636 photo/procedural and 648/810 camera
records. Maximum summary discrepancy is 1.4211e-14. All 25,132 shared V43/V95
cases reproduce all 200,408 recorded metric fields exactly, including nulls.
The [immutable primary receipt](../docs/results/v95-palette-primary-statistics-v1.json)
records checkpoint lineage, fixed-input witnesses, per-condition means and
all primary contrasts.

Most sources improve slightly in the extra 4k stages, but large adverse tails
offset those gains. V96/V97 improve 330/336 of 427 source means over V95, with
median gains +0.04068/+0.04166 dB and worst regressions −3.98915/−3.38332 dB.
V95 itself improves 400 sources over V43 while its worst source falls 6.35319 dB.
These are held-out development failures, not reasons to exclude difficult
evaluation photos or put them into training. Photo SSIM improves slightly,
while chroma MAE worsens. Keep the adverse values alongside the gains.

Actually viewed both known/unseen camera boards at original size: all 24 saved
triplets represented in 32 distinct native160 cells. The four joint outputs
are close in these fixed crops, with clean edges but remaining smoothing and
faint unevenness. Independent AHD reference grain/interpolation is not exact
RGB truth. The [camera viewing receipt](../docs/results/v95-palette-native-camera-review-v1.json)
binds both boards and their actual observations. The first board command used
photo-style RawNIND labels and failed before creating any output; using the
actual recorded camera labels completed the board. No inference was repeated.

Added V96/V97 final4k primary points to the PSNR history, now 37 selected
endpoints from 17 studies. All 35 earlier point dictionaries and 16 earlier
source records remain exactly equal to the archived prior registry. The new
PNG was actually viewed; CSV/JSON/PNG/SVG/PDF and the history table agree.
Updated the existing quality report and navigation without changing frozen
numerical inputs, old machine receipts, model settings or running workers.

Publication checks passed: 25 static hashed references, 138 local Markdown
links, exact equality of the earlier history records, and clean Ruff/syntax
and whitespace checks. Both live plan guards pass: all 1,796/16 declared
inputs and 64/71 frozen files remain unchanged in the main/queued jobs.

The texture stage has completed; color and GFX stages continue under the same
controller. Their independent scalar/array checks and actual native views,
plus the already queued lower-noise photo views, remain pending. V43 remains
the working reference. No quality promotion, extra training, speed study,
100MP qualification or SOTA claim follows from these primary statistics.
