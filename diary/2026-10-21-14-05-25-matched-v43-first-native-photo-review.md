# Inspect first native crops from the completed V43 quality arms

Recorded: 2026-10-21T14:05:25-07:00 (America/Los_Angeles).

The full production evaluation is running under the same live photo worker,
PID3661319/create1792616248.47. At this observation it has completed 32 of 443
sources and 8,064 per-image scores, with no stage result yet. Keep the full
seven-stage comparison unchanged; do not rank models from partial means.

Inspect the native crop artifacts already completed for the suite's first two
fixed validation entries. They were selected by source order before prediction.
For each source, inspect original V43, final V93/V94/V95 and both observed-input
RawNIND gain adapters: twelve triplets, 36 native 160-pixel panels in total.
Each uses ISO12800-prior, RGGB, display exposure 1 and tile ROI [48,48,160,160].

Independently verify PNG hashes, matching source/ROI/conditioning/display
metadata, native panel rectangles and byte-identical noisy/exact synthetic GT
panels across methods. Stack complete existing PNGs using pixel pastes only;
all output row pixels are checked against their originals. Actually view all
four resulting montages with original resolution. No model inference or pixel
resampling is introduced by this review.

In the paraglider crop, all joint models remove visible grain and retain the
canopy outline, but the fine suspension lines remain much weaker than the
clean target across all six methods. Some broad variation remains in the new
controls' smooth orange region. This crop does not establish whether its thin
lines are recoverable at the chosen noise level or a clear V95-over-V43 gain.

In the glass-building crop, all four joint models preserve window divisions and
balcony geometry more clearly than the RawNIND adapters. Clouds and fine rail
detail remain softer than the exact clean target. Differences among the four
joint models are subtle; this single scene does not establish the requested
new-model improvement or broad real-photo superiority.

[Actual viewing evidence](../docs/results/v43-quality-photo-first-native-review-v1.json)
records all four image hashes and source-specific observations. Private detailed
review SHA: `488697783fb10651c2f536aba913306412b8f9ceeb5aa73fc884e68710e33dfc`.
Continue to full photographic/real, weak-detail/flat, color and GFX results and
their native views before interpreting the full comparison. V43 remains the
reference and speed work stays deferred.

