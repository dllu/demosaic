# Qualify pale feather detail for future training

Recorded: 2026-10-27T12:56:02-07:00 (America/Los_Angeles).

Reviewed eight title-selected real photographic candidates while V124 continued. The previous goal turn produced measured14k progress evidence and updated current documentation; it was progress, not a wait. This turn prepares better future weak-detail data without changing any active or queued run.

Actually viewed all eight native bin4 sources and eight original JPEG512 cells, three initial proposal boards plus one revised net board, and all four associated original1024 follow-ups. One additional saved augmented reader target was viewed at native256. No source HDD access, new sensor observations, RAW decode, model call or optimizer work.

Qualified Basile Morin's pale swan-feather region. Its local64 has11/16 eligible fine-band blocks below5% contrast and the full256 context186/256, before attenuation. Native1024 resolves physical barbs, tips and faint shadows. The whole context is not uniformly weak or certified noiseless. The net-shop JPEG has visible alias/moire/processed-looking edges and gets no specialized annotation; the grass-feather target is mostly high contrast and also gets none. Both remain ordinary photos. A visually similar backlit swan image is not added just to inflate counts. No source exclusions.

Prepared `configs/low-contrast-training-rois-cleaned90778-v2.json`:34 regions, preserving all33 prior example objects and the same90778/2303/2255 manifest bytes/memberships. Four candidates were already reviewed; four new IDs bring the deduplication ledger to1923. This is not an exhaustive or randomly sampled corpus audit. V134/V135 and their source-order policy remain bound to33 regions; no new training job is queued by this data addition.

Actual clean-reader checks visit all34 regions over83 reads. All33 common regions forced to identical source identities/indexes plus four ordinary/four procedural controls match8,060,928 FP32 values exactly. RNG is unchanged, CUDA uninitialized and neural Module calls forbidden. The new saved draw at index1229/seed1299 includes photographic contrast attenuation;252/256 eligible blocks are below5%, compared with186/256 in the unaugmented context. Native source and actual training contrast are different quantities.

Independent UINT32 area2/FP64 display checks19,277,808 bin4 source PNG channels,25,165,824 native JPEG/sheet channels,3,145,728 proposal source channels,832,560 target/local channels and196,608 actual-reader channels. All compared pixels match exactly. Mirrored-FFT DCT checks816 proposal blocks with max statistic error6.11e-16. Existing data tests pass48 cases in4.27s. Two earlier invocations named missing test files and executed no tests; their logs are preserved, then the corrected discovered suite completed. No neural work or prefix was repeated.

Published source decisions, full credits, five native PNGs and source/reader/audit bindings. Updated README/current model/data/research guides with the qualified future bank, while preserving frozen trial data and explicit unmeasured trained quality. V120 remains the general recommendation; weak real detail and broad SOTA superiority remain open.

Publication verification checks2297 content bindings,26 frozen plans,176 active local links and five byte-exact public PNGs. All22 controllers and V124's original worker are alive, with latest recorded training step15825 at verification; selector and existing trial inputs are unchanged. The initial link check treated relative links inside the verbatim archived Markdown code fence as active diary links. Its source/log is preserved; v2 excludes fenced source text from link extraction while still checking the exact archived bytes. No neural or pixel work was replayed.

[Source admission report](../docs/repetitive-material-source-review.md) ·
[Measurement/reader receipt](../docs/results/repetitive-material-source-review-v1.json) ·
[Publication verification](../docs/results/repetitive-material-source-publication-v1.json).

The exact prior current-source guide is preserved below and privately at
`.cache/current-quality-20261023-v1/repetitive-material-scout-20261027-v1/previous-current-source-guide-v1.md`.

## Exact previous current-source guide

Previous file SHA256: `6b3c2484aa413cd6a7d913fbe4032ea36c1cb9c0234de0aed516d6f72e1a07c1`.

```markdown
# Current photographic-source review

**The prepared future dataset contains 90,778 training photos and 33 reviewed
regions.** The latest actual inspection retains 38 new sources and withholds
two display/artwork-heavy photographs from that separate future set. Fine
dragonfly-wing mesh and subtle pitted stone extend the detail bank. The ledger
contains 1,919 unique inspected IDs. Source cleanup has no measured model-quality
result and does not certify every retained photo pristine.

[Latest native inspection](v124-second-source-review.md) ·
[All 40 decisions and credits](results/v124-second-source-decisions-v1.csv) ·
[Selection, pixel audit and reader evidence](results/v124-second-source-review-v1.json).

## Data currently used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison | 90,786 / 14 | Both 20k reviews complete; small weak-detail changes and a worse joint-arm ADC tail |
| V124/V125 mean-loss comparison | 90,784 / 20 | V124 control training; V125 follows on fixed original inputs |
| Completed V126–V128 pilots | 90,783 / 23 | Shadow/feature terms show no useful gain at 1k |
| V129 data / V130 precision pilots | 90,782 / 27 | Both 1k reviews complete; small mixed detail changes |
| V131/V132 spatial trial | 90,781 / 29 | CPU/CUDA checks pass; full 20k and progress reviews queued; quality unmeasured |
| V133 quota trial | 90,781 / 29 | CPU/CUDA checks pass; 5% quota against original V131 50% control; full/progress reviews queued |
| V134/V135 cleaned-data cohort | **90,778 / 33** | Four discarded CPU/CUDA checks complete; full 20k and endpoint reviews queued; quality unmeasured |

[Mean-loss trial](conditional-mean-training.md) · [Spatial trial](raw-spatial-training.md) ·
[Quota trial](reviewed-quota-training.md) · [FP32 pilot](training-precision-pilot.md).

The [full source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation: the spatial trial's 50% reviewed quota
visits 46.36% of its photos in 20k updates; the same seed/cohort at 5% would visit
69.26%. That counterfactual is metadata only. The separate V133 trial measures
the quota change against the original V131 control. Its current data stay fixed.

The [33-region catalogue](../configs/low-contrast-training-rois-cleaned90778-v1.json)
preserves all 31 preceding example objects. The latest manifest removes exactly
two rows from the preceding 90,780-photo future set, preserving remaining line
bytes/order and validation/test counts of 2,303/2,255. Earlier
[plaster and butterfly additions](v124-first-source-review.md) remain available.
Neither new membership nor new annotations replace active or queued inputs.
An optional [ordinary-photo epoch order](photographic-epoch-order.md) visits
all prepared photos within the audited 20k schedule; its quality is unmeasured.
The [V134/V135 comparison](photo-epoch-training.md) now queues its controlled
training test on this cohort after four real implementation checks.

## Latest inspection and detail support

An immutable V124 trace prefix through the 11,200-step boundary ends at its last
traced Commons batch, 11,100. In the new 5,600 < step ≤ 11,200 window, 247
photographic draws leave 218 draws/217 IDs after review deduplication. Eight
highest-loss distinct sources per noise group and eight remaining high-gradient
sources nominate 40 actual inspections. Only the first noise view is traced;
evolving weights, exposure, camera transforms and noise confound scores.

Actual viewing covers seven sheets, 40 thumbnails, 80 native256 source/target
cells, ten native1024 follow-ups and six native512/local64 proposal boards.
The withheld frames are real photographs dominated by emissive display media
or decorative tile artwork. Physical sculptures, a fossil and a photographed
scale-model car remain ordinary data. Natural bokeh/panning blur, distant
softness, native grain and uncertain processing are recorded rather than
automatically turned into exclusions. Originals/caches remain intact.

The selected wing local64 has four of 16 fine-band blocks below 5% contrast and
nine at 5–10%; revised pitted stone has 14 below 5%. The reader uses full contexts
that also contain stronger edges. Its two saved native256 draws have 57/256 and
82/256 valid blocks below 5%, without attenuation on those particular draws.
The configured photographic attenuation probability remains 25%. Local source
contrast, actual augmented-target contrast and corpus-wide coverage are different
quantities. [Images, definitions and limits](v124-second-source-review.md).

## Executable verification

Independent heap ranking reproduces all 40 nominations. Original/cache hashes,
native cells, sheets, large follow-ups and proposal pixels are checked; UINT32
binning/FP64 display agrees within 1 DN8. Mirrored-FFT DCT reproduces 96 local
annotation blocks and 512 saved-reader blocks.

Actual `CleanDataset` checks visit all 33 regions over 80 reads and match
7,667,712 common FP32 values across 31 fixed-identity regions and four ordinary/
four procedural controls. Global RNG remains unchanged, CUDA stays uninitialized
and no neural/noise/RAW/optimizer work occurs. Preparation uses bin4 → geometry
→ final area2, zero optical PSFs, corrected paired32 and native128 catalogues.
[Training pipeline](training-pipeline.md).

The ledger supports deduplication, not exclusions or uniform corpus coverage.
Historical snapshots, source traces, failed preparation evidence and receipts
retain their bytes; the [local-time diary](../diary/2026-10-27-10-50-28-v124-second-source-curation.md)
preserves the prior current guide. Both GFX pairs, camera JPEGs and siblings
remain outside training.
```
