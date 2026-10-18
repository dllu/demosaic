# Full-frame mixed16 quarter GFX native inspection

The frozen full-frame GFX worker3151327/1792327436.66 completed successfully
and exited. Its report SHA256 is
`c70a32ec5a56ba92feafc4501f06eb8ad3d0bcb4252603aa32bc7b3bc10f608a`.
The quality controller moved to three cached cameras; profiling and CUDA EMA
measurement still wait behind its exact owner. No GPU work was restarted.

Built and actually viewed the six-method native board using the existing
saved-PNG reader. All24 triplets cover the standing sky, building, foliage and
chain-link fence ROIs. All32 saved board cells preserve160×160 source pixels
exactly; shared source/ROI/noise/exposure/WB/matrix/reference settings match.
The report and24 original PNG hashes were checked again after viewing.

The board is
`/mnt/external/demosaic/benchmarks/mixed16-quarter-native-review-v1/gfx-native.png`,
SHA256`a2200f8eb1a67b80b4142208a6fcf7938ee97e6c5202bb516dc751f952f6f0be`.
The [public native-view receipt](../docs/results/mixed16-quarter-GFX-native-view-v1.json)
is byte-identical to its private counterpart, SHA256
`cf95916f54f16aacfc424e780e50f2f19001b9ce26e9441ead29c792777f863d`.
It records checkpoint hashes and the metadata-bearing board receipt.

Both new10k models retain substantial colored grain in sky/building and weak
noisy foliage/fence structure. DINO looks somewhat smoother locally but has
no clear fine-detail advantage in these four views. Mature V43/V63 have much
cleaner fields and more continuous fence structure, while foliage remains
soft. RawNIND has wavy/soft building and fence patterns. The sharper ISO100
f/5.6 capture differs in optics, exposure duration, time and moving content;
it remains an independently demosaiced qualitative reference, never exact GT.

Subsequently inspected all24 triplets/36 native cells from the closed
three-camera report. The [receipt](../docs/results/mixed16-quarter-three-camera-native-view-v1.json)
retains source/ROI/noise/display metadata through its board receipt. These six
cached512 contexts span Q2, a7RII and GFX50R; the RawNIND row is another model
output, not GT. The new models remain close to noisy Malvar on dark water and
bright/out-of-focus plane regions, with stronger colored grain than mature
controls on GFX50R stone. No clear new DINO fine-detail advantage is visible.

This brings the current review to108 viewed triplets/146 native cells across
known/unseen cameras, the final-matched exact-GT photos, analytic targets,
full-frame GFX and three cached cameras. The twelve RGB16 exports exist; full
integrity is still the queued artifact audit's job. Color/statistical review
and final budget decision remain pending. No new inference, score, training
extension or model promotion was performed. V43 remains the README working
reference.
