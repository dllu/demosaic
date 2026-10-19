# Inspect completed known-camera crops while full427 evaluation runs

Previous goal turn was a verified wait on the exact live full-photo review
worker. Revalidated reviewer2028199 and worker2169408/creation1792377682.30 plus
all queued follower identities. The full suite continues, most recently31,703
of74,424 saved records; no observation timeout caused a restart or duplicate job.
The global quality/speed goal remains active and incomplete.

Advanced the required manual review using the already completed known-camera
stage. Actually viewed all six original PNG triplets with view_image at original
resolution: two fixed scenes for V80, V81 and genuine V63. Each PNG is512×192,
with three unresized160×160 panels. All six PNG hashes and sidecar metadata match
their completed summary. The three methods share source/crop/ROI, noise estimate,
variance multiplier, display exposure, WB and color matrix. Noisy and auxiliary
reference panel pixels are identical across methods. Nothing was resampled,
re-encoded, enlarged or newly inferred for this viewing.

In2pilesofplates, all three remove strong colored noise and preserve broad plate
edges and a thin pale zigzag. Low-contrast horizontal tonal variation in the
auxiliary AHD reference remains smoother in each output. In7D-1, all three clean
the green/gray panels and dark cross; an isolated bright point remains visible
in the vertical dark bar. Their broad edge/tonal appearance is very close at this
display. The auxiliary reference contains fine pattern/noise that the outputs
smooth, without establishing from this view which part is true scene detail.
No clear bank-specific advantage or new failure is visible in these two ROIs.

These are preliminary observations at a fixed8-bit native preview, not exact
RGB error findings or a full quality decision. The real registered low-noise RAW
has an independently demosaiced AHD RGB reference; primary scores use measured
CFA samples. It is not exact RGB GT. Full-precision numerical review and the
complete fixed suite remain necessary. No crop, checkpoint or threshold was
selected from these observations.

Saved a hash-bound partial view record at the review root's
manual-review-known-fresh-v1.json and linked it from the preparation registry.
It records6 viewed triplets/18 displayed panels, complete metadata and narrative
observations, manual_review_completed:false and quality_decision:null. It does
not satisfy the required two synthetic exact-GT report triplets or replace
viewing every final board/cell. Unseen, GFX foliage/fence/sky/buildings/lights,
carriers/flats, hues/highlights and actual V43/RawNIND comparisons remain to be
viewed in the completed review. No own GPU work overlapped the existing worker.

An initial generic link check treated relative prepared-crop filenames as paths
from the working directory. Resolved them against the actual prepared manifest
and verified both cached NPZ hashes. The complete record now uses absolute paths
while preserving original relative paths in its source sidecars. All37 immutable
bindings, method/ROI/display checks and diff checks pass. The reviewer and all
followers remained live, with34,524 saved full-suite records at the final check.
