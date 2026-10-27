# Current photographic-source review

**The prepared future dataset contains90,776 training photos and35 reviewed
regions.** The final V124 high-loss review inspected40 new sources, retained38,
withheld two grainy/artwork-heavy photographs and added one mixed-contrast leaf
context. The ledger has1,963 unique inspected IDs. These data changes have no
measured restoration-quality result or source-wide pristine guarantee.

[Latest high-loss review and native examples](v124-final-source-review.md) ·
[All40 decisions and credits](results/v124-final-source-decisions-v1.csv) ·
[Selection, pixels and reader evidence](results/v124-final-source-review-v1.json) ·
[35-region catalogue](../configs/low-contrast-training-rois-cleaned90776-v1.json).

## Data used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k reviews complete; small weak-detail changes and worse joint-arm ADC tail |
| V124/V125 mean-loss comparison |90,784 /20 | V124 original20k training complete; V125 training runs; full endpoint quality pending |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k |
| V129/V130 and V136/V137 pilots |90,782 /27 | Completed1k reviews show small mixed changes without clear fine-mesh recovery |
| V138 frozen-parent branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and native review queued after V125 completion |
| V131/V132 spatial trial |90,781 /29 | CPU/CUDA checks pass; V13120k runs, V132 follows; full/progress reviews queued |
| V133 quota trial |90,781 /29 | CPU/CUDA checks pass;5% versus V131's50% quota; full/progress reviews queued |
| V134/V135 cleaned-data cohort |90,778 /33 | Four checks complete; matched20k/full reviews queued; quality unmeasured |
| Latest prepared future bank | **90,776 /35** | Two future-only exclusions and one leaf region; actual reader/pixel checks pass; no training-quality claim |

Existing recipes, source-order headers, source cohorts and budgets remain
unchanged. The optional [photographic epoch order](photographic-epoch-order.md)
visits all prepared photos at its audited20k budget; its matched
[V134/V135 training test](photo-epoch-training.md) retains90,778/33. The
[source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation and reviewed quotas. Prepared source
changes do not imply training convergence or improved reconstruction.

## Latest inspection

The complete V124 diagnostic trace contains1,344 first-view draws from84 traced
Commons batches through19,800, within its completed20k training. The new
11,200<step≤20,000 window has452 photographic draws. Prior-review/cohort
filtering leaves385 draws/383 IDs. Eight distinct highest-loss sources per
noise group plus eight remaining high-gradient sources nominate40 inspections.
Changing weights, camera transforms, exposure and noise confound these losses;
there is no automatic quality label or replay of scored augmentations.

Actual viewing covers seven sheets,40 thumbnails/80 native256 cells, sixteen
native1024 follow-ups, five whole native-bin4 views, four native source/target
proposal boards and the saved clean-reader leaf draw. The noisy concert photo
and painting-dominated altar are withheld only from a future cohort. Original
photos/caches remain intact. Real sculptures, specimens, natural bokeh,
specular water and saturated flowers remain ordinary photography. Softness,
native grain and uncertain processing are recorded without a pristine-source
claim. [Images, exact decisions and limits](v124-final-source-review.md).

The leaf annotation has4/16 eligible local fine-band blocks below5% contrast
before attenuation, alongside stronger veins, droplets, boundaries and soil.
The proposed down, spider-adjacent fibres and rock fields have0/16,1/16 and0/16;
they stay ordinary photos without specialized weak annotations. Quiet or soft
background does not itself qualify a fine-detail region. The earlier
[pale-feather admission](repetitive-material-source-review.md),
[wing mesh/pitted stone](v124-second-source-review.md) and
[plaster/butterfly regions](v124-first-source-review.md) remain preserved.

## Executable verification

Independent heap ranking reproduces all40 nominations. Source/cache hashes,
original native pixels and sheet cells verify. Independent UINT32 area2/FP64
display checks8,696,880 target channels;29 differ by1 DN8 from primary FP32.
Mirrored-FFT DCT checks1,344 source/augmented blocks with maximum error7.78e−16.

Actual35-region sampling visits every region over85 reads and matches8,257,536
common FP32 values across34 fixed-identity regions and four ordinary/four
procedural controls. The old catalogue is rebound to the same future manifest
only for this control. Source exclusions and bank expansion intentionally can
change sampled identities. Python/NumPy/Torch RNG stays unchanged, CUDA remains
uninitialized and neural/noise/RAW/optimizer calls are zero.

The saved leaf draw is index796/seed866, not contrast-attenuated, with12/256
eligible fine-band blocks below5%. The configured25% attenuation policy stays
unchanged; one draw does not establish training-wide weak-detail coverage.
The source manifest drops exactly two train rows while preserving every other
line's bytes/order, all34 previous region objects and validation/test at2,303/
2,255. [Training pipeline](training-pipeline.md).

The1,963-ID ledger supports deduplication rather than exclusions or uniform
corpus coverage. Historical snapshots, traces and machine receipts preserve
their bytes; the [local-time diary](../diary/2026-10-27-16-35-35-v124-final-source-curation.md)
records this update. Both GFX pairs, camera JPEGs and siblings stay outside
training, with originals read-only. Trained quality on the new data is unmeasured.
