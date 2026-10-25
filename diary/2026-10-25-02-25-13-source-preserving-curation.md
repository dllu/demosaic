# Preserve photographic draws across corpus curation

Recorded: 2026-10-25T02:25:13-07:00 (America/Los_Angeles).

Measured the sampling effect of applying the latest 90,802-source cohort to
the original seed64/20k recipe. Sixty-two rows are removed relative to V117's
90,864-source manifest. Plain filtered-index sampling changes 98,605 of 112,330
scheduled photographic source draws and affects all 10,032 Commons batches.
This is substantial source resampling beyond the intended membership change.
The domain schedule stays 5,013 paired / 4,955 native / 10,032 Commons; weak,
flat, other procedural and reviewed ROI quotas also retain their schedule.

Added optional `PhotoSamplingReference`: draw from the immutable original
ordered training list and retry excluded identities before opening a cache.
The active training records must be an exact metadata/cache-path subset.
Reviewed ROI override precedes rejection so an unused nominal excluded source
does not consume extra geometry RNG. Eligible ordinary photos retain uniform
rejection sampling. Without a reference, the original path stays exact.

The full prospective schedule contains 53 excluded-photo draws across 52
Commons batches. The implemented sampler matches the independently proposed
source counts for every one of the 112,330 photographic draws; all unaffected
source choices and source-selection RNG states match the original. Four
additional nominal excluded choices are overridden by reviewed ROIs without
retries. Counts are prospective data allocation, not completed training.

The real native256 augmented-reader audit exercises 93 selected indices,
including all 53 excluded draws, 16 ordinary unaffected examples, procedural
examples, all six ROI sources and four nominal excluded/ROI overrides, with
overlap deduplicated. All 93 default-reader outputs match the frozen V117
implementation. Forty unchanged future targets match exactly, while the 53
excluded-photo targets are replaced. The future reader never opens an excluded
cache. All 26,148,864 compared FP32 clean values match. Global Python/Torch RNG
is unchanged and CUDA is uninitialized. These data audits forbid module calls
and make zero model, noise, optimizer or RAW calls.

The trainer records and snapshots the reference payload/hash. Resume rejects
reference changes or disabling the mode; the recipe controller pins the
optional reference input too. Eleven new tests pass, including eight actual
toy-network optimizer updates across full/split/resumed runs, exact model/EMA/
Adam/RNG continuation and reference snapshot checks. Thirty-four related
geometry/ROI/lazy-domain tests pass, including the disabled reader's exact
comparison with the historical V95 reader. The earlier ROI training integration
test is deselected; successful research inference is not rerun for bookkeeping.

[Current source guide](../docs/next-source-tail-review.md#preserve-draws-for-a-matched-curation-comparison)
and [corpus guide](../docs/corpus-source-review.md) document the optional mode.
[Machine evidence](../docs/results/source-preserving-curation-v1.json) binds the
implementation, full schedule, real reader, tests and original/future manifests.
Private source/audit roots are `cleaned-corpus-schedule-v1/` and
`photo-sampling-reader-v1/` under `.cache/current-quality-20261023-v1/`.

All 72 original V117/V118 frozen source files retain their hashes. Current
recipes, model selection, historical receipts and the completed PSNR history
remain unchanged. At 02:23 PDT the original V117 controller/child are live with
finite logged scalars through 13,475/20,000 steps. This feature prepares a fair
later curation experiment; it is not a measured restoration-quality gain.

Publication verification checks all five implementation/test bindings and 55
frozen reader modules, adopts the successful test runs without replaying them,
resolves 62 local links and confirms ten protected model/recipe/curation/history
files match HEAD. The private proof is
`source-preserving-curation-publication-verification-v1.json` under the cache
base. Its verification imports no Torch and performs no neural/noise work.
