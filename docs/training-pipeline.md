# Training data, augmentation and sampling

**Current quality recipes use native 256/B16, geometry before final downsampling,
zero optical PSF augmentation and loading only the selected data domain.**
Commons targets come from the completed, reviewed Quality Images corpus;
camera-linear targets and registered paired RAW supply complementary supervision.
[Current model](current-model.md) · [Source review](current-source-loss-review.md).

The newest prepared dataset has 90,778 training photos and 33 reviewed regions.
Its V134/V135 CPU/CUDA checks pass; completed production quality is still
unmeasured. Existing trials retain their frozen inputs:

| Trial | Commons sources / regions | Reviewed fraction within photographs |
| --- | --- | ---: |
| Running [V124/V125 mean-loss comparison](conditional-mean-training.md) |90,784 /20 |5% |
| Queued [V131/V132 spatial comparison](raw-spatial-training.md) |90,781 /29 |50% |
| Queued [V133 quota comparison](reviewed-quota-training.md) |90,781 /29 |5% |
| Queued [V134/V135 cleaned data/order comparison](photo-epoch-training.md) |90,778 /33 |5%, with replacement versus epochs |

Corpus size is distinct from scheduled source diversity. The
[full 20k source audit](training-source-schedule-coverage.md) finds that the spatial
trial's 50% reviewed quota gives 56,256 draws to 29 sources and visits 46.36% of its
photo corpus. A 5% quota on the same seed/cohort would visit69.26%, based on
metadata only. This supports testing the quota at fixed architecture/data;
restoration quality under that change is unmeasured. V133 now queues that
quota-only20k comparison, reusing V131 and preserving the original trials.

An optional [ordinary-photo epoch order](photographic-epoch-order.md) now has a
full actual-reader audit on the prepared 90,778/33 set. At the same seed70/20k/B16
and 5% quota it visits all photos, versus 69.26% with replacement. Current jobs
keep their original sampling; the new order has no trained-quality result.
The [V134/V135 runner](photo-epoch-training.md) has four actual16+2 checks
complete and queues its 20k comparison and full endpoint/native reviews.

## Augmentation before the final reduction

The current `augmentation_downsample: 2` path is:

1. Decode the licensed source, honor EXIF/ICC, convert to linear sRGB and average
   4×4 source cells into a uint16 cache.
2. Choose a crop at least twice the final patch resolution. Apply exact quarter
   turns/flips at that higher resolution.
3. On the 20% projective branch, combine crop scaling and bounded rotation/shear
   in one resampling operation at twice the output resolution. Otherwise use
   area scaling there. Cached pixels are never stretched to admit a small source.
4. Apply the configured optical PSF, then average 2×2 linear cells to the final
   native 256 target. **Current Commons and native recipes set PSF probability 0.**
5. Optionally attenuate photographic contrast, then apply exposure/camera
   transforms, Bayer sampling, Poisson/read noise and 16-bit ADC simulation.

There is no geometric interpolation after the final reduction. Synthetic shapes,
weak textures and smooth controls use the same higher intermediate resolution.
Interpolation error is reduced, not eliminated; binning does not certify every
source free of grain, blur or processing. [Reader implementation](../src/demosaic/data.py).

Native camera-linear targets use `raw_clean_augmentation_downsample: 2`, preserving
their camera coordinates/color metadata. The current native manifest has 128
scenes,106 used for training. Corrected registered paired32 references use their
valid sensor masks and exact phase-preserving transforms; their dense RGB
estimates are not exact GT. [Native data](native-raw-targets.md) ·
[Paired masks/sampling](paired-camera-sampling.md).

## Reviewed photographic regions

`reviewed_roi_catalogue` binds each region to an exact active training source,
manifest/cache/crop hashes and an aligned512×512 bin4 context. Native256 takes
that context before augmentation and final area2; smaller patches stay within
it. The reader validates membership, dtype, shape, bounds and target hashes.
Resume rejects a changed catalogue or fraction.

`reviewed_roi_fraction` is conditional on a **photographic Commons draw**. It
does not replace flat or synthetic samples. Selection precedes cache loading:
an overridden photograph opens only its reviewed source. An independent selection
stream preserves untreated source and geometry draws. A fixed ordered
`photo_sampling_reference_manifest` uses rejection sampling for future exclusions
without changing unaffected identities. [Implementation](../src/demosaic/photo_sampling.py).

The [33-region future catalogue](../configs/low-contrast-training-rois-cleaned90778-v1.json)
preserves all 31 prior example objects. It adds fine dragonfly-wing mesh and
subtle pitted stone, with native views and descriptive local contrast. The actual
reader visits all 33 regions in its 80-read verification. These checks
prove executable data binding, not improved model quality or uniformly pristine
source texture. [Native examples and limits](v124-second-source-review.md).

## Current recipe sampling and targets

Domain selection happens first: approximately25% paired RAW,25% native-camera
synthetic and 50% Commons. Only the selected loader advances. Sample indices
retain their global step/B16 positions, workers start on first use, and prefetch
stops at the requested endpoint. Paired/native steps do not load or augment
discarded Commons batches. [Scheduling implementation](../src/demosaic/train.py).

Within Commons, the configured proportions mean:

| Option | Meaning |
| --- | --- |
| `flat_fraction: .10` |10% smooth fields/ramps |
| `synthetic_fraction: .20` |20% total synthetic, including the weak-texture quota |
| `weak_texture_fraction: .15` |15 percentage points within that20%;5% remains other synthetic |
| Remaining70% |Ordinary photographs or reviewed photographic regions |
| `photographic_low_contrast_fraction: .25` |25% conditional on photographs; preserve each channel mean while scaling deviations by a draw in[1/8,1/2] |
| `reviewed_roi_fraction` |A separate conditional photographic quota,5% or50% in the current controlled trials |

The remaining camera/exposure and physical-noise draws follow clean preparation.
All Bayer phases, signed noise/black handling, broad camera matrices, WB and
highlight behavior retain their recipe-specific settings. Per-step deterministic
data seeds prevent earlier source substitutions from shifting later noise streams.

V124/V125 load16 clean target slots once and create two independent simulated
noise views; paired steps remain16 observations. The spatial trial uses one
view. Additional noise views do not add source diversity. The
[source-schedule audit](training-source-schedule-coverage.md) counts each clean
slot once and distinguishes future planned selections from actually logged draws.
The earlier [retained-target contrast audit](training-target-contrast-coverage.md)
finds faint-band content in a bounded18-step prefix; flat surfaces and soft
backgrounds can also contribute, so counts cannot replace material inspection.

## Internal training artifacts

Exact studies use their [frozen control/treatment recipes and runner](raw-spatial-training.md).
An independent new run should bind its intended manifests/catalogue, parent EMA,
encoder revision/hash, output directory and complete LR horizon. The trainer
snapshots code/config/data identities and rejects incompatible resumes.
Changed reviewed-region quotas/catalogues now reject before model construction;
the actual V133 check exposed and corrected the previous late validation.
Portable endpoints, optimizer checkpoints, retained progress snapshots and
discarded CPU/CUDA implementation checks remain distinct artifacts.

Source cleanup changes separate future manifests. Inspect original and binned
pixels before exclusion; high loss, natural defocus, grain or a source title is
not an automatic rejection rule. [Per-source loss trace](source-loss-diagnostics.md)
uses detached existing predictions without another neural forward. Originals
stay read-only; both GFX pairs/JPEGs/siblings and protected validation/test
memberships remain outside training. [Current review](current-source-loss-review.md).

## Batch-size sweep

Completed sweeps retain **batch16**. On the measured4×→2× RGB/native pipeline it
reaches30.81 native 256 patches/s; batch32 is only1.3% faster with 13.41GB versus
6.95GB peak CUDA allocation. [Actual-pipeline measurements](current-pipeline-batch-sweep.md).
The later [RAW-head sweep](raw-kernel-training-batch-sweep.md) also retains16.
These are observations on their recorded architectures/shared-machine states,
not current spatial/two-view throughput or convergence claims. Quality precedes
new speed work; the 100MP/10s inference target remains open.

Larger patches also alter admissible source coverage when preserving4×→area2
without upscaling. [Original context/corpus comparison](training-context-original4k-review.md).
A patch-size or batch-size change therefore needs a separately identified
quality experiment rather than being treated as a free throughput improvement.

## Matched corpus and augmentation pilot

The completed [V32/V34 comparison](geometry-corpus-v34-v36-review.md) measures
a+.50990 dB full 427-photo gain for4×→geometry→area2 over8×→geometry at the matched
first1,000 updates. This is the evidence for the adopted augmentation order;
the exact historic cohorts, schedules and speed observations remain in that report.

Earlier readiness claims, trial chronology and the exact previous pipeline page
are preserved in the [local-time diary](../diary/2026-10-27-08-52-27-source-schedule-coverage.md).
Original machine receipts and experiment evidence retain their bytes.
