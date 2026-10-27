# Current photographic-source review

**The latest pass retains39 newly inspected sources and withholds one
poster-dominated image from a future cohort.** The deduplicated review ledger
has1,799 IDs. Four additional inspected physical-detail contexts extend the
future bank to27 regions on90,782 training sources. Earlier experiments keep
their frozen data; [V129 completed its new-cohort pilot](reviewed-detail-training-pilot.md)
and [V130 tests FP32 on those inputs](training-precision-pilot.md).
Source cleanup alone does not prove quality gains.

[Latest inspection and native views](v123-source-review-through15800.md) ·
[All40 decisions/credits](results/v123-source-loss-through15800-decisions-v1.csv) ·
[Trace, independent verification and actual reader proof](results/v123-source-loss-through15800-review-v1.json).

## Current data snapshots

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k complete; full endpoint evaluation collecting |
| V124/V125 mean-loss comparison |90,784 /20 | Four checks reused; production queued after frequency review |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k; complete native review |
| V129 data pilot / V130 precision trial |90,782 /27 | V1291k complete: no useful visible gain; V130 tests FP32 on the same inputs |

[V123 continuation](v123-memory-guard-recovery.md) ·
[Mean-loss trial](conditional-mean-training.md) ·
[Shadow-pilot results](reviewed-shadow-pilot-quality.md) ·
[Completed V128 feature pilot](v128-feature-pilot-quality.md) ·
[V129 curated-data trial](reviewed-detail-training-pilot.md).
Earlier frozen memberships, recipes, quotas and blur policies remain intact;
V129 declares its new cohort as a separate experiment.

The [27-region catalogue](../configs/low-contrast-training-rois-cleaned90782-v1.json)
preserves all23 previous example objects, adding fox fur, quail feather, thin
iron fence/foliage and weathered timber contexts. The future manifest removes
exactly one training row from90,783 and preserves all remaining row bytes/order;
validation/test counts remain2,303/2,255. Private GFX pairs, JPEGs and siblings
stay outside training. Existing23-region catalogue bytes remain intact.

## What the latest inspection establishes

Disjoint original/resumed V123 trace prefixes through15,800 contain1,248
recorded draws,896 photographic draws from847 IDs. After the prior1,759-ID
ledger,692 eligible draws from690 IDs remain. Eight distinct high-loss sources
per noise group plus eight remaining high-gradient cases receive actual native
inspection. Losses depend on evolving weights, exposure, noise and camera
transforms; they nominate inspection rather than label source quality.

Actually viewed: seven sheets,80 native256 source/target cells, five native1024
follow-ups and four source512/local-target64 boards. The flat advertising poster
is withheld from the future photographic quota. The title “Aquarell” belongs to
a photographed illuminated sign, which is retained. Other originals include
grain, softness or coarse processing-like texture; their inspected area8 targets
retain coherent physical structure, without certifying noiseless microtexture.

The new bank is mixed contrast. The fox annotation has8/16 local blocks at2–5%
relative fine-band contrast; none is below2%. Feather/fence/timber annotations
are stronger. Native inspection verifies physical structure; contrast counts
are descriptive, not an automatic admission rule or corpus distribution.
[All native views and source/ROI metadata](v123-source-review-through15800.md).

## Admission and verification

Review original and binned pixels before excluding a source. A flat-poster
reproduction, real illuminated lettering and physical relief need distinct
judgments. Art/HDR/text titles, high loss, low contrast and a defocused background
are not automatic rejection rules. Originals remain intact; exclusions affect
separate future manifests.

Independent heap ranking reproduces all40 nominations. Native source/sheet/
large-view pixels match exactly; independently binned targets agree within1DN8
under FP64 versus FP32 display. Actual `CleanDataset` checks visit all27 regions,
compare23 common regions at fixed identity/index plus four ordinary and four
procedural controls:6,094,848 FP32 values match over66 clean reads. Different
banks need not choose the same random source IDs. No neural/noise/RAW/optimizer
work occurs; global RNG remains unchanged and CUDA stays uninitialized.

Current preparation uses bin4 → geometry → final area2, zero optical PSFs,
corrected paired32 and native128 catalogues. [Training pipeline](training-pipeline.md).
The1,799-ID ledger is for review deduplication, not training membership,
exclusions or a uniform corpus audit. Previous current-page text is retained
exactly in the [timestamped diary](../diary/2026-10-27-01-11-18-v128-resumption-source-review.md#exact-preceding-current-source-page),
with its hash and independent byte copy. All earlier machine receipts remain intact.
