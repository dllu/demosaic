# Queue full-photo local-detail comparison after V116 review

Recorded: 2026-10-24T19:22:24-07:00 (America/Los_Angeles).

The small local-detail analysis found a weak high-noise stratum containing only
feather/fur. Added an archive analyzer to broaden that measurement to all427
photographic development sources without new neural work. The fixed three
priors and four CFAs provide5124 paired source/condition/CFA observations and
96075 unique16px source blocks. Four CFA responses pool within a source before
equal-source means; all strata report their actual coverage. The16 analytic
sources in the photographic suite are excluded.

The earlier same-source lookup found all12 RGGB material cases in the full
archive. Target arrays differ from the CPU pilot by at most1.19e-7, with shared
WB/matrix. That proximity is not exact noisy-input identity. The new audit
uses full V114/V116 archive targets, input fingerprints and predictions as its
own matched comparison, rather than borrowing older CPU measurements. No data
or noise is regenerated, and held-out material remains outside training.

Nine tests pass: closed-form .5/.75 gains and+.25 change through a complete
three-prior/four-CFA fixture; mismatched packed/variance/colors/WB/matrix,
changed target, missing fields, duplicates and unsupported policy rejection.
An actual frozen-source readiness run uses48 retained V114 single-view
observations from the same four materials across all CFAs. All15 self-comparison
summary groups differ by exactly zero, and independent cosine/FFT coefficients
agree within1.47e-14. It imports no Torch and adds zero neural/encoder calls,
optimizer updates, noise observations or RAW decodes. This is readiness, not
V116 quality. The original scripts, plans, logs and numeric outputs are retained.

A separate analytic archive fixture checks unequal source coverage explicitly:
225 versus15 eligible blocks, four CFAs each, with candidate gains.75/.25.
The source-balanced result is.5 while the pooled result is.71875, matching the
closed form in all three condition labels. It generates deterministic test
arrays, not neural predictions or new sensor-noise draws. Its source and
[additive proof](../docs/results/local-detail-source-weighting-proof-v1.json)
are retained separately; the already launched queue and proof plan stay unchanged.

Launched a separate CPU controller behind the exact original V114/V116 matched
review owner1300076/create1792873556.91. The new owner is
1737151/create1792894919.16, bound to its frozen source and plan. It is live and
waiting. Start reserves are16GiB available RAM/2GiB output; runtime RAM floor
8GiB and600s analysis bound. It preserves failures without automatic retry.
All original training, evaluator, independent audit and comparison jobs retain
their owners, sources, budgets and dependencies. No model/default change or
automatic documentation publication follows this scalar diagnostic.

Published [the queued evidence](../docs/results/local-detail-archive-queued-v1.json)
and updated [the current diagnostic](../docs/local-material-detail.md#full-photo-follow-up)
and [running data-trial guide](../docs/fine-detail-data-training.md). V116 was
live at9200/20000 around19:21 PDT; nine validation monitors have finite scores
and unchanged comparator/panel definitions. Trained quality remains pending.

