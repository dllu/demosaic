# Review real weak and fine texture training sources

Recorded: 2026-10-21T23:12:16-07:00 (America/Los_Angeles).

The original primary photo worker/controller and secondary native dependency
waiter remain live, with continuing score-file growth and no completed panel
yet. No new GPU job or current-model/source/config change.

Used the existing frozen large training membership to select24 previously
unreviewed material/mesh/foliage title cues. The existing source renderer also
adds one unreviewed hash-ordered control, giving25 new sources. Titles are
selection cues only: no model loss or performance score selected them. All
395 previously viewed sources were skipped. Every selected ID is already in
the88484-source training cohort; holdouts and withheld sources are not used.

Actually inspected all five source sheets: context thumbnail, original-native256
and native256 target from the4x cache plus final area2. All25 are retained at
the viewed scales; no additional clear exclusion. Coherent yarn/mesh, material,
foliage and bark details remain valid targets. Stronger geometry and naturally
defocused backgrounds are not automatically weak sharp texture or bad photos.
Moss Malvern is a car-model name, illustrating a false metadata cue. Source
quality remains a visual target-scale decision rather than a title/software
classification.

Inspected six full native8 contexts to locate focused training ROIs, then two
new ROI sheets, covering six candidate regions plus the same control. The
six inspected regions contain gray yarn fibers, faint fishing-net lines,
gray wire braid, subtle white-painted wood grain, pale lichen filaments and
same-color cloth folds/crease edges. Surrounding contrast varies; the catalogue
does not label whole images low contrast or claim resolved silk fibers.
The selected net ROI excludes the face. All origins align to even bin4 pixels;
512x512 cache crops reduce by area2 to256x256 without target interpolation.

The [prospective training ROI catalogue](../configs/low-contrast-training-rois-v1.json)
records source metadata/licenses, train split, original/cache identities,
bin4 ROIs and raw crop/float32 target hashes. Original SHA1 and complete cache
SHA256 were checked by the existing renderer; all six crop/target hashes were
recomputed. This is a data catalogue for a later controlled sampling/weighting
experiment. No sampler, augmentation/noise policy, membership or training run
is applied. Geometric augmentation would require separate ROI boundary checks.

Published two exact source-quality figures with full metadata/credits, for
gray yarn and subtle white fence grain. Thumbnails alone resize; source and
binned target crops retain their native pixels and have different physical
fields of view. Display exposure1, no sensor noise or restoration. These are
source-quality examples, not noisy/denoised/GT performance triplets.

Cumulative actual visual coverage is420 unique sources:396 retained/24withheld.
This preserves the original371-source membership-freeze decisions and all
current training/evaluation manifests. It is targeted review, not a full-corpus
manual inspection or an estimated defect rate. The
[review receipt](../docs/results/low-contrast-training-source-review-v1.json)
has SHA256 `b7781c392932eeca0f92605a53e52e81286ad545b04baf540dc2a7709b663b11`.
No new model forward, noise draw, quality/speed claim or promotion. V43 remains
the working reference; the full goal is still unmet.

