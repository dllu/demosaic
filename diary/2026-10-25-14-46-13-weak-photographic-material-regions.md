# Prepare visually checked weak photographic material regions

Recorded: 2026-10-25T14:46:13-07:00 (America/Los_Angeles).

Prepared an optional **fourteen-region photographic material catalogue** for
the future 90,787-source cohort. It preserves all six existing example objects
and adds eight existing, eligible sources. No training-source membership,
sampling quota, loss mask or augmentation setting changes. V119 continues its
original six-region / 90,791-source full 20k experiment from V115 Small.

The previous turn made concrete progress: ca8d78e published 336 actual source
reviews, four withholds, future 90,787 manifests and the targeted 16-pair reader
check. At this turn's first actual process poll, V119's worker identity matched
PID 3134902/create 1792951461.96 and it had reached 13,575/20,000. All four queued
evaluation/audit/matched/native-camera comparison owners were also confirmed
live by PID and creation time, rather than trusting status files alone.

Initial material nomination used twelve retained sources from the completed
top768 review. All twelve aligned source/target contexts and six local512-source
/64-target pairs were actually viewed. Local linear measurements showed that
these are mixed-contrast fine-material contexts, without making them a global
low-contrast class. None was added to this new bank. This changes the next
selection step instead of treating a scene label as proof of weak detail.

A pure metadata query reuses completed historical source scores. Among active
future 90,787 sources outside the older 32-region catalogue, 195 candidates have mean-RGB
linear SD .015–.05, gradient RMS .0015–.025 and clipped fraction≤.01. Sixteen
varied physical subjects were nominated by titles and then actually viewed at
native source/target resolution. Eight selected sources contain weak brick
joints, plaster cracks/pigment boundaries, bronze patina, dark snowy roofs and
branches, mud-ridge boundaries, wavelets and sand-ripple ridges. The other eight
remain ordinary eligible photos: several scored low because their centers were
mostly blank sky/background. Physical insect edges and dark artifact outlines
also do not automatically make a weak material region.

All eight selected local512-source/native64-target pairs were actually viewed,
with no resized pixels. Independent NumPy reconstruction from original JPEG
pixels reproduces 393,216 bin4 uint16 values and 98,304 native8 FP32 values exactly.
Local luminance SD ranges .01139–.02727. This differs from the historical whole
context mean-RGB statistic. Dark low absolute contrast is not asserted uniformly
low relative contrast; naturally soft mud is labeled accurately, and individual
mud/sand grains are not asserted resolved. Across both selection stages, 28 unique
contexts/56 native256 cells and 14 local512/64 pairs were inspected. These ROI
review counts are separate from the earlier cumulative corpus-cleanup ledger.

The actual loader reuses the preceding byte-identical frozen reader sources.
It exercises all fourteen ROI choices at native256 using V119's data options
and the source-preserving 90,864 reference. Four ordinary-photo and two procedural
samples reproduce reused stored controls exactly, without rereading the parent
controls. All 20 outputs / 3,932,160 FP32 values are finite. Expected source caches
are opened, no excluded/held-out cache is reached, and Python/NumPy/Torch global
RNG states are unchanged. CUDA remains uninitialized. There are no neural
forwards, noise observations, RAW decodes or optimizer updates. This is a
discarded clean-data preflight at the existing 5% conditional-photo probability,
not an executed training schedule or an applied production change.

The first local-view helper failed at import because an underscore module name
did not match a hyphenated filename. It failed before pixel work; its source/log
and failure receipt remain preserved. A new corrected file completed once.
Earlier pending receipts retain their original bytes; the additive final
reader receipt records successful completion.

Published three exact-byte context strips and their native512/64 local figures
for brick grid, sea wavelets and plaster cracks, with original author/license,
ROI, display and crop hashes. Only full-source thumbnails resize pixels.
Updated the current pipeline guide, including its stale claim that V102/V103
were still running. The earlier six-versus32 comparison had mixed results;
this new bank is untrained, and its restoration-quality effect is unknown.
All actual scripts, views and receipts are preserved under
`.cache/current-quality-20261023-v1/low-contrast-material-ROIs-20261025-v1/`.

[Current guide and native examples](../docs/weak-photographic-targets.md) ·
[Prospective 14-region catalogue](../configs/low-contrast-training-rois-cleaned90787-v1.json) ·
[Actual visual review](../docs/results/weak-photographic-targets-review-v1.json) ·
[Completed reader check](../docs/results/weak-photographic-targets-v1.json).
