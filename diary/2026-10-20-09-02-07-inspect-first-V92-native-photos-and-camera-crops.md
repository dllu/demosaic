# Inspect first V92 native photos and camera crops

Verified the source-frozen full427 evaluation is genuinely live: controller
1278489/create1792506281.09 and child1343568/create1792509889.08. The child CPU
user time advances from1717.49s at this turn's start to2235.63s; the
per-image stream contains67089 complete lines. Scores remain uninterpreted.
Boundary/known/unseen stages have completed. The exact mature-precision
controller1331098/create1792508313.33 remains waiting, with zero children and
no GPU output. No GPU job was launched, stopped or overlapped.

The live producer already emitted the six fixed photo triplets and six each
known/unseen camera triplets. Copied all18 source PNGs and metadata into a
separate early-native cache, retaining original identities. Built three
complete method-by-case boards through the unchanged native-board builder:
V90 historical original4000, V92 head-only original4000 and V63 parent20k;
two cases each. Same noisy/reference pixels, ROI/noise/exposure metadata and
checkpoint hashes are checked across methods, and all30 native160px cells
are independently rehashed. A one-off preparation helper initially assumed
camera crops had nested model metadata. It stopped after the photo board;
the common existing identity reader correctly handles camera top-level label/
SHA fields. The already built photo board was verified/reused; no producer
file, inference or model state changed.

Actually viewed all30 cells through original-resolution image tools. Fine
canopy cords remain absent in all three methods; V92 is visually close to its
parent on canopy/building. Known plate and patch crops have similar soft edges
and small color changes. Unseen fruit crops stay strongly smoothed. These
selected views do not establish a clear V92 gain. Camera references are
independent LibRaw AHD, not exact GT. Two V92 noisy/restored/exact-GT photo
triplets and all three boards are published byte-exact with full metadata.

This completes30 of125 required native cells only. Remaining95 GFX/analytic/
hue/highlight cells, full scalar/source audits and quality decisions remain.
No early numerical decision, model promotion or training extension. Final
packaging must retain matching original pixels; the interim record cannot
impersonate complete native review. No new software tests are needed for
these artifact/documentation additions; actual source/PNG/cell/Markdown-link
checks pass. V43 and README remain unchanged.

Report: docs/late-rgb-head-only-interim-native.md.
Evidence: docs/results/late-rgb-head-only-interim-native-v1.json.
Source cache: .cache/benchmarks/late-rgb-head-only-v92-early-native-v1/.
The broad SOTA, decisive real-photo superiority and actual100MP/10s goals are
still unmet/unproven; the goal remains active.
