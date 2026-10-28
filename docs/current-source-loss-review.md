# Current photographic-source review

**The prepared future dataset contains90,774 training photos and36 reviewed
regions.** The latest balanced V125/V131 high-loss review inspected40 additional
sources and retained all40. Four fixed material proposals remain ordinary
photos, without specialized weak annotations; manifest/catalogue bytes are
unchanged. The ledger has2,043 unique inspected IDs. Prepared data changes have
no measured restoration-quality result or source-wide pristine guarantee.

[Latest inspection and native examples](v125-v131-source-review.md) ·
[All40 decisions and credits](results/v125-v131-source-decisions-v1.csv) ·
[Selection, pixels and unchanged-data evidence](results/v125-v131-source-review-v1.json) ·
[36-region catalogue](../configs/low-contrast-training-rois-cleaned90774-v1.json).

## Data used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k reviews complete; small weak-detail changes and worse joint-arm ADC tail |
| V124/V125 mean-loss comparison |90,784 /20 | V124 original20k training complete; V125 training runs; full endpoint quality pending |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k |
| V129/V130 and V136/V137 pilots |90,782 /27 | Completed1k reviews show small mixed changes without clear fine-mesh recovery |
| V138 frozen-parent branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and native review queued after V125 completion |
| V139 memory-only branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and matched102-input review queued after the V138 review chain |
| V131/V132 spatial trial |90,781 /29 | [V1311k progress](v131-progress1000-quality.md) has mixed changes and no clear mesh recovery; original20k continues, V132 follows |
| V133 quota trial |90,781 /29 | CPU/CUDA checks pass;5% versus V131's50% quota; full/progress reviews queued |
| V134/V135 cleaned-data cohort |90,778 /33 | Four checks complete; matched20k/full reviews queued; quality unmeasured |
| Latest prepared future bank | **90,774 /36** | Previous exclusions/mixed white-plumage addition preserved; latest40-source inspection changes no data; actual reader/pixel evidence retained |

Existing recipes, source-order headers, source cohorts and budgets remain
unchanged. The optional [photographic epoch order](photographic-epoch-order.md)
visits all prepared photos at its audited20k budget; its matched
[V134/V135 training test](photo-epoch-training.md) retains90,778/33. The
[source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation and reviewed quotas. Prepared source
changes do not imply training convergence or improved reconstruction.

## Latest inspection

Immutable sparse traces cover V125 through3,400 and V131 updates(1,900,6,000].
Filtering against2,003 previously inspected IDs and the current prepared cohort
leaves192 photographic draws/180 distinct IDs. Four distinct losses per arm/noise
group, then four additional gradient choices per arm, nominate20 inspections per
arm/40 total. Changing weights, camera, geometry, exposure and noise confound
scores; V125 logs its first noise view only. Nomination introduces no automatic
quality label or scored augmentation replay.

Actual viewing covers seven sheets with40 thumbnails/80 native256 cells, four
native1024 follow-ups, four whole native-bin4 views, four source/target proposal
boards and four further native1024 material views:23 files. All40 sources retain
coherent photographic detail after binning. Sculptures, physical station mosaics,
engraved stone and printed clothing are assessed in their scene context. Native
grain/depth softness/strong edge rendering remain disclosed where visible.
Original/cache files remain intact.

Fixed fur, marble, leaf-vein and wood-grain local annotations each have0/16
eligible fine-band blocks below5% contrast. Marble and leaf have10/16 and13/16
between5–10%; fur/wood are stronger. All remain ordinary photos. Whole-context
lower counts can include quiet background or smooth surfaces and do not alone
establish useful weak material. ROIs were not retuned after statistics.
[Native images, exact decisions and limits](v125-v131-source-review.md).

The [preceding V131 review](v131-source-review.md) preserves two future-only
exclusions (a painting reproduction and processed-looking arch source) and one
mixed white-plumage context, with3/16 local eligible blocks below5% and coherent
feather barbs. Its stronger rice-husk/wing/green-feather proposals stay ordinary.

Earlier [mixed leaf veins](v124-final-source-review.md),
[pale feather barbs](repetitive-material-source-review.md),
[wing mesh/pitted stone](v124-second-source-review.md) and
[plaster/butterfly regions](v124-first-source-review.md) remain preserved.

## Executable verification

Independent heap nomination reproduces all40 new choices/groups/logged cases.
Source/cache/native pixels and sheets verify. UINT32 area2/FP64 display
checks7,864,320 strip-target channels, with24 one-DN8 rounding differences within
the declared≤1DN8 bound;832,560 proposal-target channels match exactly.
Mirrored-FFT DCT checks1,088 fixed source blocks within2.23e−15.

The preserved actual36-region reader proof visits every region over87 reads
and matches8,454,144 common FP32 values across35 fixed-identity regions and four
ordinary/four
procedural controls. The old catalogue is rebound to the same future manifest
only for this comparison. Exclusions/bank expansion can change selected IDs;
global sampler identity equality is not claimed. That proof retains unchanged
Python/NumPy/Torch RNG and uninitialized CUDA. It is not replayed for this
inspection because no data/catalogue/reader bytes change. New neural/noise/RAW/
optimizer calls are zero.

The preceding saved white-plumage draw is index1,599/seed1,669, not contrast-attenuated,
with105/256 eligible fine-band blocks below5%, including background. The25%
attenuation policy remains unchanged. One draw does not establish training-wide
weak-detail coverage. Its preparation dropped exactly two train rows while
preserving all other line bytes/order and35 prior region objects. The latest
inspection preserves the entire90,774/36 manifest/catalogue, including
validation/test at2,303/2,255. [Training pipeline](training-pipeline.md).

The2,043-ID ledger supports deduplication, not exclusions or uniform corpus
coverage. Historical snapshots/traces/machine receipts preserve their bytes;
the [local-time diary](../diary/2026-10-27-20-32-44-v125-v131-source-review.md)
records this update. Both GFX pairs, camera JPEGs and siblings remain held out,
with originals read-only. Trained quality on the new data is unmeasured.
