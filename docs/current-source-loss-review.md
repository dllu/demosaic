# Current photographic-source review

**The prepared future dataset contains 90,773 training photos and 37 reviewed
regions.** The latest balanced V125/V131 inspection retains 39 of 40 new sources,
withholds one grainy/speckled coastal photograph and adds one mixed-contrast leaf
region. All 36 prior region objects remain exact. The ledger reaches 2,083 unique
inspected IDs. Prepared data changes have no measured restoration-quality result
or source-wide pristine guarantee.

[Latest inspection and native examples](v125-v131-source-review-5600-9800.md) ·
[All 40 decisions and credits](results/v125-v131-source-decisions-5600-9800-v1.csv) ·
[Selection, pixels, data and reader evidence](results/v125-v131-source-review-5600-9800-v1.json) ·
[37-region catalogue](../configs/low-contrast-training-rois-cleaned90773-v1.json).

## Data used and prepared

| Use | Commons train sources / reviewed regions | State |
| --- | --- | --- |
| V122/V123 frequency comparison |90,786 /14 | Both20k reviews complete; small weak-detail changes and worse joint-arm ADC tail |
| V124/V125 mean-loss comparison |90,784 /20 | V124 original20k training complete; V125 training runs; full endpoint quality pending |
| Completed V126–V128 pilots |90,783 /23 | Shadow/feature terms show no useful gain at1k |
| V129/V130 and V136/V137 pilots |90,782 /27 | Completed1k reviews show small mixed changes without clear fine-mesh recovery |
| V138 frozen-parent branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and native review queued after V125 completion |
| V139 memory-only branch |90,782 /27 | CPU/CUDA16+2 checks pass; original1k and matched102-input review queued after the V138 review chain |
| V140 neighboring-gradient memory |90,782 /27 | CPU/CUDA16+2 pass; fresh1k and matched102-input review queued, reusing612 predictions |
| V131/V132 spatial trial |90,781 /29 | [V1311k progress](v131-progress1000-quality.md) has mixed changes and no clear mesh recovery; original20k continues, V132 follows |
| V133 quota trial |90,781 /29 | CPU/CUDA checks pass;5% versus V131's50% quota; full/progress reviews queued |
| V134/V135 cleaned-data cohort |90,778 /33 | Four checks complete; matched20k/full reviews queued; quality unmeasured |
| Latest prepared future bank | **90,773 /37** | One grainy coastal source withheld; mixed leaf region added; all 36 prior regions preserved; actual reader/pixel evidence retained |

Existing recipes, source-order headers, source cohorts and budgets remain
unchanged. The optional [photographic epoch order](photographic-epoch-order.md)
visits all prepared photos at its audited20k budget; its matched
[V134/V135 training test](photo-epoch-training.md) retains90,778/33. The
[source-schedule audit](training-source-schedule-coverage.md) distinguishes
available photos from actual visitation and reviewed quotas. Prepared source
changes do not imply training convergence or improved reconstruction.

## Latest inspection

Immutable sparse traces cover V125 updates (3,400, 5,600] and V131 (6,000, 9,800].
Filtering 2,043 previously inspected IDs and the current cohort leaves 150
photographic draws/distinct IDs. Up to four distinct singleton losses per
arm/noise group, followed by alternating gradient choices, nominate 20 per arm.
V125 has only one eligible high-noise source; three missing slots become gradient
choices. Changing weights, camera, geometry, exposure and noise confound scores;
V125 logs its first noise view only. Nomination is not an automatic quality label
or replay of scored augmentation.

Actual viewing covers seven sheets with 40 thumbnails/80 native256 cells, six
native1024 follow-ups, six whole native-bin4 views, four fixed source/target
proposal boards and four further native1024 views: 27 files. The coastal scene's
visible grain and pale sky speckles make its future clean targets less reliable;
their cause is unknown. Physical reliefs, statues and clothing prints remain
photography. Strong native edge rendering and depth softness remain disclosed.

The new leaf region retains coherent veins, hairs and surface detail after
binning. Its fixed local64 contains 4/16 eligible fine-band blocks below 5%, with
another 5 at 5–10%; other edges are stronger. Three proposals stay ordinary:
grey feathers have stronger fine contrast; the plinth is mostly smooth despite
16 weak blocks; snow counts include quiet sky. Low measured contrast alone does
not establish useful fine material. Coordinates were not retuned after statistics.
[Native images and exact decisions](v125-v131-source-review-5600-9800.md).

The [preceding 40-source inspection](v125-v131-source-review.md) retains all 40
sources without new specialized annotations. Earlier
[mixed white plumage](v131-source-review.md),
[leaf veins](v124-final-source-review.md),
[pale feather barbs](repetitive-material-source-review.md),
[wing mesh/pitted stone](v124-second-source-review.md) and
[plaster/butterfly regions](v124-first-source-review.md) remain preserved.

## Executable verification

Independent heap nomination reproduces all 40 choices/groups/logged cases.
JPEG/cache hashes, native pixels and sheets verify. UINT32 area2/FP64 display
checks 7,864,320 strip-target channels, with 37 one-DN8 differences within the
≤1DN8 bound; 832,560 proposal-target channels match exactly. Ten source1024
views, six whole-bin4 views and four source512 panels verify independently.
Mirrored-FFT DCT checks 1,088 fixed source blocks within 1.34e−15.

The actual 37-region reader visits every region over 89 clean reads and matches
8,650,752 FP32 values across 36 fixed-identity common regions, four ordinary and
four procedural controls. The parent catalogue is rebound to the same future
manifest only for this comparison. Exclusions/bank expansion can change selected
IDs; global sampler identity equality is not claimed. Python/NumPy/Torch RNG
remain unchanged and CUDA is uninitialized. Neural calls are forbidden.

The saved new leaf draw is index617/seed687 and actually contrast-attenuated,
with 254/256 eligible fine-band blocks below 5%, including quiet areas; 140 are
below 2%. Its native256 pixels and all 256 contrast blocks have an independent
NumPy/FFT audit. This one sample does not establish training-wide coverage. The
existing 25% photographic attenuation probability, zero PSF and geometry before
area reduction remain unchanged. [Training pipeline](training-pipeline.md).

Preparation removes exactly one train row and preserves every remaining manifest
line byte/order and all 36 prior region objects. Validation/test remain
2,303/2,255. The 2,083-ID ledger supports deduplication, not exclusions or uniform
corpus coverage. Original snapshots, failures and completed rendering prefixes
remain preserved. Both GFX pairs/JPEGs/siblings remain held out, with protected
originals read-only. All existing jobs retain their declared cohorts, source
order, parents, budgets and deadlines. Trained quality on the prepared data is
unmeasured.
