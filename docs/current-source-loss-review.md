# Current photographic-source review

**The prepared future dataset contains 90,778 training photos and 34 reviewed
regions.** The latest source-only inspection admits one pale swan-feather
context and declines specialized net/grass-feather annotations. The preceding
high-loss review withheld two display/artwork-heavy photos and added wing mesh
and pitted stone. The ledger contains1,923 unique inspected IDs. These data
changes have no measured model-quality result or source-wide pristine guarantee.

[Latest texture admission and native examples](repetitive-material-source-review.md) ·
[Latest high-loss inspection](v124-second-source-review.md) ·
[All 40 decisions and credits](results/v124-second-source-decisions-v1.csv) ·
[Selection, pixel audit and reader evidence](results/v124-second-source-review-v1.json).

## Data currently used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison | 90,786 / 14 | Both 20k reviews complete; small weak-detail changes and a worse joint-arm ADC tail |
| V124/V125 mean-loss comparison | 90,784 / 20 | [14k progress measured](v124-progress14000.md); original20k control continues, V125 follows |
| Completed V126–V128 pilots | 90,783 / 23 | Shadow/feature terms show no useful gain at 1k |
| V129 data / V130 precision pilots | 90,782 / 27 | Both 1k reviews complete; small mixed detail changes |
| V131/V132 spatial trial | 90,781 / 29 | CPU/CUDA checks pass; full 20k and progress reviews queued; quality unmeasured |
| V133 quota trial | 90,781 / 29 | CPU/CUDA checks pass; 5% quota against original V131 50% control; full/progress reviews queued |
| V134/V135 cleaned-data cohort | **90,778 / 33** | Four discarded CPU/CUDA checks complete; full 20k and endpoint reviews queued; quality unmeasured |
| Newest prepared future bank | **90,778 / 34** | Swan-feather region passes actual reader and pixel checks; no training run or quality claim |

[Mean-loss trial](conditional-mean-training.md) · [Spatial trial](raw-spatial-training.md) ·
[Quota trial](reviewed-quota-training.md) · [FP32 pilot](training-precision-pilot.md).

The [full source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation: the spatial trial's 50% reviewed quota
visits 46.36% of its photos in 20k updates; the same seed/cohort at 5% would visit
69.26%. That counterfactual is metadata only. The separate V133 trial measures
the quota change against the original V131 control. Its current data stay fixed.

The [34-region catalogue](../configs/low-contrast-training-rois-cleaned90778-v2.json)
preserves all33 previous example objects. V134/V135 keep the
[original33-region catalogue](../configs/low-contrast-training-rois-cleaned90778-v1.json).
The current manifest removes exactly
two rows from the preceding 90,780-photo future set, preserving remaining line
bytes/order and validation/test counts of 2,303/2,255. Earlier
[plaster and butterfly additions](v124-first-source-review.md) remain available.
Neither new membership nor new annotations replace active or queued inputs.
An optional [ordinary-photo epoch order](photographic-epoch-order.md) visits
all prepared photos within the audited 20k schedule; its quality is unmeasured.
The [V134/V135 comparison](photo-epoch-training.md) queues its controlled
training test on90,778/33 after four real implementation checks. Its existing
source-order policy is not reused with a changed region catalogue.

## Latest texture inspection

Eight title-selected training photos were viewed at native bin4 and original
JPEG resolution, with four proposal/original1024 follow-ups. Swan plumage has
186/256 eligible fine-band blocks below5% contrast before attenuation. The
net-shop JPEG has alias/moire concerns and the grass-feather proposal is mostly
high contrast, so neither gets a specialized weak annotation. All eight remain
ordinary photographic sources. [Decisions, native images and limits](repetitive-material-source-review.md).

Actual34-region sampling visits every region over83 clean reads, with8,060,928
common target values exact against the prior reader under controlled identical
region identities and ordinary/procedural controls. A saved new feather draw is
attenuated and has252/256 eligible blocks below5%; source and augmented counts
are distinct. Independent area2/display/FFT verification passes without model,
noise, RAW or optimizer execution. The latest48 focused data tests pass.

## Latest high-loss inspection and detail support

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

The preceding33-region `CleanDataset` checks visit all33 regions over80 reads and match
7,667,712 common FP32 values across 31 fixed-identity regions and four ordinary/
four procedural controls. Global RNG remains unchanged, CUDA stays uninitialized
and no neural/noise/RAW/optimizer work occurs. Preparation uses bin4 → geometry
→ final area2, zero optical PSFs, corrected paired32 and native128 catalogues.
[Training pipeline](training-pipeline.md).

The ledger supports deduplication, not exclusions or uniform corpus coverage.
Historical snapshots, source traces, failed preparation evidence and receipts
retain their bytes; the [local-time diary](../diary/2026-10-27-10-50-28-v124-second-source-curation.md)
preserves an earlier current guide. The
[new local-time entry](../diary/2026-10-27-12-56-02-repetitive-material-source-review.md)
preserves the exact33-region guide before this update. Both GFX pairs, camera
JPEGs and siblings remain outside training.
