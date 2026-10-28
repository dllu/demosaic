# Current photographic-source review

**The prepared future dataset contains90,774 training photos and36 reviewed
regions.** The latest V131 high-loss review inspected40 new sources, retained38,
withheld a painting reproduction and a processed-looking architectural source,
and added one mixed-contrast white-plumage context. The ledger has2,003 unique
inspected IDs. These data changes have no measured restoration-quality result
or source-wide pristine guarantee.

[Latest inspection and native examples](v131-source-review.md) ·
[All40 decisions and credits](results/v131-source-decisions-v1.csv) ·
[Selection, pixels and reader evidence](results/v131-source-review-v2.json) ·
[36-region catalogue](../configs/low-contrast-training-rois-cleaned90774-v1.json).

## Data used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k reviews complete; small weak-detail changes and worse joint-arm ADC tail |
| V124/V125 mean-loss comparison |90,784 /20 | V124 original20k training complete; V125 training runs; full endpoint quality pending |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k |
| V129/V130 and V136/V137 pilots |90,782 /27 | Completed1k reviews show small mixed changes without clear fine-mesh recovery |
| V138 frozen-parent branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and native review queued after V125 completion |
| V131/V132 spatial trial |90,781 /29 | [V1311k progress](v131-progress1000-quality.md) has mixed changes and no clear mesh recovery; original20k continues, V132 follows |
| V133 quota trial |90,781 /29 | CPU/CUDA checks pass;5% versus V131's50% quota; full/progress reviews queued |
| V134/V135 cleaned-data cohort |90,778 /33 | Four checks complete; matched20k/full reviews queued; quality unmeasured |
| Latest prepared future bank | **90,774 /36** | Two future-only exclusions and one mixed white-plumage region; actual reader/pixel checks pass; no training-quality claim |

Existing recipes, source-order headers, source cohorts and budgets remain
unchanged. The optional [photographic epoch order](photographic-epoch-order.md)
visits all prepared photos at its audited20k budget; its matched
[V134/V135 training test](photo-epoch-training.md) retains90,778/33. The
[source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation and reviewed quotas. Prepared source
changes do not imply training convergence or improved reconstruction.

## Latest inspection

The immutable sparse V131 source-loss prefix through1,900 contains160 draws
from ten traced Commons batches:114 photographic draws/82 IDs. Filtering against
1,963 inspected IDs and the previous prepared cohort leaves46 draws/46 IDs.
Up to eight highest distinct losses per noise group, then remaining highest
gradient losses, nominate40 inspections. Changing weights, camera, exposure and
noise confound scores; no automatic quality label or scored augmentation replay
is introduced.

Actual viewing covers seven sheets with40 thumbnails/80 native256 cells, eight
native1024 follow-ups, six whole native-bin4 views, four source/target proposal
boards and four further native1024 material views, plus the saved reader draw.
A framed painting reproduction and processed-looking arch/cloud/foliage source
are withheld only from a future cohort. The latter is real photography; coarse
posterized-looking texture and strong outlines motivate target-quality caution,
without identifying its processing cause. Original/cache files remain intact.

Mixed white plumage adds coherent feather barbs:3/16 local eligible fine-band
blocks below5% contrast, alongside stronger feather boundaries, grass and
background. Rice-husk, brown-wing and green-feather proposals have0/16 each;
they remain ordinary photos without specialized weak annotations. Fixed ROIs
were not retuned after statistics. Quiet background alone does not qualify
fine material. [Native images, exact decisions and limits](v131-source-review.md).

Earlier [mixed leaf veins](v124-final-source-review.md),
[pale feather barbs](repetitive-material-source-review.md),
[wing mesh/pitted stone](v124-second-source-review.md) and
[plaster/butterfly regions](v124-first-source-review.md) remain preserved.

## Executable verification

Independent heap nomination reproduces all40 choices. Source/cache/native
pixels and sheets verify. UINT32 area2/FP64 display checks7,864,320 strip-target
channels, with26 one-DN8 rounding differences;832,560 proposal-target channels
match exactly. Mirrored-FFT DCT checks1,344 source/augmented blocks within6.67e−16.

Actual36-region sampling visits every region over87 reads and matches8,454,144
common FP32 values across35 fixed-identity regions and four ordinary/four
procedural controls. The old catalogue is rebound to the same future manifest
only for this comparison. Exclusions/bank expansion can change selected IDs;
global sampler identity equality is not claimed. Python/NumPy/Torch RNG stays
unchanged, CUDA remains uninitialized and neural/noise/RAW/optimizer calls are zero.

The saved white-plumage draw is index1,599/seed1,669, not contrast-attenuated,
with105/256 eligible fine-band blocks below5%, including background. The25%
attenuation policy remains unchanged. One draw does not establish training-wide
weak-detail coverage. The manifest drops exactly two train rows and preserves
all other line bytes/order, all35 prior region objects and validation/test at
2,303/2,255. [Training pipeline](training-pipeline.md).

The2,003-ID ledger supports deduplication, not exclusions or uniform corpus
coverage. Historical snapshots/traces/machine receipts preserve their bytes;
the [local-time diary](../diary/2026-10-27-17-40-27-v131-source-curation.md)
records this update. Both GFX pairs, camera JPEGs and siblings remain held out,
with originals read-only. Trained quality on the new data is unmeasured.
