# Current photographic-source review

**The latest pass retains39 newly inspected sources and withholds one painted-
tile-dominated frame from a separate future cohort.** The review ledger now
has1,839 unique IDs. Two inspected material contexts extend the future bank to29
regions on90,781 training sources: actual weak petal veins and sharp bridge mesh.
Existing training and evaluation inputs keep their frozen snapshots. Source
cleanup alone does not prove quality gains.

[Latest inspection and native views](v123-final-source-review.md) ·
[All40 decisions/credits](results/v123-final-source-decisions-v1.csv) ·
[Trace, independent verification and actual reader proof](results/v123-final-source-review-v1.json).

## Current data snapshots

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k complete; full endpoint evaluation collecting |
| V124/V125 mean-loss comparison |90,784 /20 | Four checks reused; production queued after frequency review |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k; complete native review |
| V129 data pilot / V130 precision trial |90,782 /27 | V1291k complete with small mixed changes; V130 tests FP32 on the same inputs |
| Prepared future cohort |90,781 /29 | One graphic-dominated frame withheld, weak petal/strong mesh added; reader proof passes; untrained |

[V123 training/review](v123-memory-guard-recovery.md) ·
[Mean-loss trial](conditional-mean-training.md) ·
[V129 curated-data results](reviewed-detail-training-pilot.md) ·
[V130 precision trial](training-precision-pilot.md).
Earlier memberships, recipes, quotas and blur policies remain unchanged.

The [29-region catalogue](../configs/low-contrast-training-rois-cleaned90781-v1.json)
preserves all27 preceding example objects. The manifest removes exactly one
training row from90,782 and preserves every remaining line's bytes/order;
validation/test counts remain2,303/2,255. Private GFX pairs, JPEGs and siblings
stay outside training. Existing catalogue and machine-receipt bytes remain intact.

## Latest inspection and region choices

The completed V123 traces have1,680 diagnostic draws,1,190 photographic draws
from1,125 IDs. This pass selects only final4,200-step photographs:294 draws,
with275 draws/274 IDs remaining after the prior ledger. Eight distinct high-loss
sources per noise group plus eight remaining high-gradient cases receive actual
native inspection. Losses depend on evolving weights, exposure, noise and camera
transforms; they nominate inspection rather than label bad photos.

Actually viewed: seven sheets,80 native256 source/target cells, six native1024
follow-ups and eight source512/local64 proposal boards. The withheld frame is
actual photography of painted ceramics, dominated by flat graphic imagery.
Projected night illumination, relief sculpture and engraved metal are retained
as physical scenes. Some originals show grain or distant softness; their area8
targets remain coherent, without certifying pristine/noiseless microtexture.

The new petal annotation has6/16 local blocks below2% and10/16 below5% relative
fine-band contrast. The bridge mesh is entirely≥20% contrast: fine-pattern
diversity, not uniformly weak detail. Inspected stone/coral regions remain in
ordinary training without expanding the specialized bank. An initially soft
coral proposal was revised to a focused ridge; both versions stay preserved.
Contrast counts are descriptive, not automatic admission rules or a corpus
coverage estimate. [All native views and metadata](v123-final-source-review.md).

## Admission and executable verification

Inspect original and binned pixels before excluding a source. High loss,
art/HDR/text titles, low contrast and a defocused background are not automatic
rejection rules. Keep originals intact; exclusions affect separate future manifests.

Independent heap ranking reproduces all40 nominations. Native source/sheet/large/
proposal pixels match exactly; independently binned targets agree within1DN8
under FP64 versus FP32 display. Actual `CleanDataset` checks visit all29 regions,
compare27 common regions at fixed identity/index plus four ordinary and four
procedural controls:6,881,280 FP32 values match over72 clean reads. Different
banks need not choose the same random source IDs. No neural/noise/RAW/optimizer
work occurs; global RNG remains unchanged and CUDA stays uninitialized.

Current preparation uses bin4 → geometry → final area2, zero optical PSFs,
corrected paired32 and native128 catalogues. [Training pipeline](training-pipeline.md).
The1,839-ID ledger serves review deduplication, not training membership or a
uniform corpus audit. Historical current-page revisions and decisions are in
the [local-time diary](../diary/2026-10-27-04-12-33-v123-final-source-curation.md).
