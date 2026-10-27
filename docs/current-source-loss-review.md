# Current photographic-source review

**The latest pass retains39 newly inspected sources and withholds one mural-
dominated real photograph from a separate future cohort.** The review ledger
contains1,879 unique inspected IDs. Two selected material contexts extend the
prepared bank to31 regions on90,780 training photos: subtle plaster/facade detail
and moderate butterfly wing-pattern diversity. Existing training/evaluation
inputs retain their frozen snapshots. Source cleanup alone does not prove
model-quality gains or certify every remaining photo pristine.

[Latest actual inspection and native views](v124-first-source-review.md) ·
[All40 decisions/credits](results/v124-first-source-decisions-v1.csv) ·
[Trace, independent pixel audit and actual reader proof](results/v124-first-source-review-v1.json).

## Current data snapshots

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k and numerical/selected native review complete; small weak-detail changes and joint-arm ADC tail |
| V124/V125 mean-loss comparison |90,784 /20 | V124 control training, V125 follows; original inputs fixed |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k; complete native review |
| V129 data pilot / V130 precision trial |90,782 /27 | Both1k reviews complete; small mixed precision/detail changes |
| V131/V132 spatial trial |90,781 /29 | Four CPU/CUDA checks complete; full20k production and early progress review queued; quality unmeasured |
| New prepared future cohort |90,780 /31 | Actual reader visits all31 regions; no production training or measured quality result |

[Mean-loss trial](conditional-mean-training.md) ·
[Spatial trial and progress review](raw-spatial-training.md) ·
[Completed FP32 comparison](training-precision-pilot.md).

The [31-region catalogue](../configs/low-contrast-training-rois-cleaned90780-v1.json)
preserves all29 preceding example objects. The new manifest removes exactly one
training row from90,781 and retains every other line's bytes/order; validation/
test remain2,303/2,255. Neither it nor its new regions replace an active or queued
trial's inputs. Private GFX pairs, camera JPEGs and siblings remain outside training.

## Current inspection and detail support

An immutable V124 trace prefix through5,600 contains368 draws from23 Commons
batches:271 photographic draws/266 IDs. Deduplication against the1,839-ID prior
ledger leaves203 draws/202 IDs. Eight distinct high-loss sources per noise group
plus eight remaining high-gradient sources receive native inspection. Scores
nominate inspection; evolving weights, noise/exposure and camera transforms
confound loss. Only the first noise view is traced; scored augmentation/noise
is not regenerated.

Actually viewed: seven sheets,40 thumbnails,80 native256 source/target cells,
eight native1024 follow-ups and11 distinct native512/local64 proposal boards.
The withheld frame is real photography of a flat graffiti mural dominating the
frame. Three-dimensional sculpture and painted signs within larger physical
scenes remain ordinary photographic data. Native grain, distant softness and
background bokeh are recorded explicitly. Crunchy fern/rock source texture
remains uncertain, but its coherent area8 target is retained without a pristine
fine-detail annotation. [Native examples and all decisions](v124-first-source-review.md).

The new plaster annotation has5/16 fine-band blocks below2% contrast and6/16
below5%, with stronger window/foliage edges. The wing is moderate fine-pattern
diversity, with1/16 below5% and12/16 at5–10%; neither full context is uniformly
weak. Other inspected candidates remain ordinary photos. Intrinsic source
contrast is distinct from the existing photographic attenuation: two saved
actual256px reader draws have169/256 and223/256 valid blocks below5% respectively.
These are particular draws, not whole-training or corpus coverage estimates.

## Admission and executable verification

Inspect original and binned pixels before excluding a source. High loss,
art/text titles, low contrast, grain or a defocused background are not automatic
rejection rules. Keep originals intact; exclusions affect separate future manifests.

Independent heap ranking reproduces all40 nominations. Native/source/sheet/large/
proposal pixels are checked; independent UINT32 binning/FP64 display agrees
within1DN8. Mirrored-FFT DCT reproduces144 annotation blocks. Actual
`CleanDataset` checks visit all31 regions, compare29 common regions at fixed
identity/index and four ordinary/four procedural controls:7,274,496 common FP32
values match over76 clean reads. Separate inspection of two saved attenuated
targets verifies their block counts and native display without another draw.
No neural/noise/RAW/optimizer work occurs; global RNG is unchanged and CUDA
stays uninitialized.

Preparation uses bin4 → geometry → final area2, zero optical PSFs, corrected
paired32 and native128 catalogues. [Training pipeline](training-pipeline.md).
The1,879-ID ledger supports review deduplication; it is not an exclusion list or
a uniform corpus audit. Historical decisions remain in the
[local-time diary](../diary/2026-10-27-08-27-35-v124-first-source-curation.md);
original catalogues, traces and machine receipts retain their bytes.
