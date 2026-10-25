# Complete source-family follow-up for photographic targets

Recorded: 2026-10-25T02:03:10-07:00 (America/Los_Angeles).

The preceding top256 review found repeated banknote and historical drawing
targets. A metadata inventory of the prepared 90,847-source cohort nominates
45 further unreviewed sources: 44 banknote entries and one Camesina window
drawing. This pass covers every unreviewed active match of its declared
case-insensitive rules across title, author, credit and attribution. Four notes
are found through author metadata rather than title words. It does not claim
exhaustive detection of every reproduction alias or missing credit.

The metadata cues nominate candidates without deciding membership. All eight
original-resolution sheets were actually inspected, including 45 whole-source
contexts and 90 unchanged native256 source/area8-target cells. All 45 are flat
reproductions under the reviewed photographic-target criteria. The note faces
are dominated by printed lettering/illustration, including the drawn-book
Braunschweig note; this is distinct from earlier retained photographs of open
physical manuscripts. The window plate has inked ornamental linework and
paper-like texture; its retained source metadata identifies Camesina and the
historical yearbook. No scanner, camera or assembly method is inferred.

These are subject/target-pool choices, not automatic grain/blur exclusions or
new loss rankings. They leave the earlier hard feathers, foliage, fur, dew,
masonry, physical stained glass and optical mineral sections eligible. The
future manifests have no unreviewed active matches of the declared rules.
Every new identity also belongs to the original 88,508-source screen pool;
the cumulative earlier-pool ledger now has 768 identities: 675 retained,
89 withheld and four preserved `exclude` labels. Separate arrival-native
coverage remains 153 identities and is not added to that count.

Prepared a separate 90,802-photo future cohort by removing exactly 45 training
rows from the 90,847-photo intermediate cohort. Every other literal row and its
order remains exact, including 2,303 validation, 2,255 test, 2,336 excluded and
5,919 reserved rows at 8×. Both scales have identical active membership and
source metadata apart from their cache/shape/bin fields. The original six ROI
objects are rebound without changing targets; the actual pure-NumPy
`ReviewedPhotoROIs` constructor checks all source/cache/ROI/native-target hashes,
dtype, shape and bounds. Originals and cache pixels are read-only.

Future manifest SHA256:

- 4×: `1e7410fc0a4f13563fbd030eb6cd16c43f6b48a2f416f0e14a2cde9c3ad2ebd4`.
- 8×: `7a6bd8765ce83c94e8186618056adabdd828fc7f37f94fecd4ac7bd852b37c71`.

Updated the existing [source review](../docs/next-source-tail-review.md),
[corpus guide](../docs/corpus-source-review.md) and
[incoming-data guide](../docs/incoming-commons-quality.md) to the latest cohort,
with two attributed native source-inspection examples. The original top256 and
30-source receipts, images and intermediate manifests retain their bytes.
[Latest decisions and coverage](../docs/results/reproduction-family-review-v1.json) ·
[actual six-ROI reader](../docs/results/reproduction-family-ROI-reader-v1.json).

Private executed sources, metadata rules/candidates, eight group decisions,
render evidence and the new manifests live under
`.cache/current-quality-20261023-v1/reproduction-family-review-v1/`.
The renderer differs from the preceding frozen renderer only by lifting its
24-metadata-candidate cap to cover this complete 45-source set and naming its
metadata cue accurately. It retains identical hash/display/area8 operations.
No new neural forward, optimizer update, noise observation, RAW decode or Torch
import occurs. This preparation has no measured model-quality gain yet.

At 02:01 PDT the exact original V117 controller and child remain live with
finite logged loss/gradient/LR through step 11,975/20,000. V117/V118 retain their
original 90,864-source data, owners, recipes and full budgets. V114 remains the
current general baseline; the original downstream review remains required.

Publication verification passes: both future manifests' surviving literal rows
match independently, the new 45-source set belongs to the original 88,508 pool,
and the declared metadata-rule coverage is complete for unreviewed active IDs.
All four published native source/target cells are independently reconstructed:
786,432 RGB8 values match exactly. The actual six-ROI reader receipt is adopted;
94 local links resolve. Sixteen protected files, including current model/recipes,
original receipts and the 49-point PSNR registry/figures, match HEAD. The private
`publication-verification-v1.json` records this without importing Torch or
executing a model.
