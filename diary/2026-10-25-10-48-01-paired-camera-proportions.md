# Preserve paired camera proportions while adding reviewed scenes

Recorded: 2026-10-25T10:48:01-07:00 (America/Los_Angeles).

Prepared a separate83-ID/71-group paired manifest from the registered51-ID
extension and the corrected train32 reference masks. All102 new reviewed cases
and their crops remain exact to the original admission. Original sources,
manifests and receipts remain unchanged; protected/GFX scenes stay held out.

Added optional camera-weighted scene sampling. The expanded data would otherwise
raise Sony's share from24/32 to60/71 groups. Explicit probabilities preserve
75% Sony,12.5% Canon6D,9.375% NikonZ6 and3.125% NikonD40, choosing groups uniformly
within each camera. The default retains the exact original RNG sequence.
Canonical probabilities are checkpointed; incompatible resume is rejected.

The93 focused tests passed, including real cached-reader sampling, deterministic
indices, RNG isolation, invalid weights and exact interrupted CPU toy training.
A separate actual native256 reader check exercised all71 groups and all four
corrected caches:76 samples/54,789,464 finite tensor values. Eleven default-reader
indices match the frozen pre-feature reader exactly (7,930,054 values). The
seed65 full20k schedule has5021 paired/4966 native/10013 Commons batches and
80,336 paired draws with the declared camera proportions. This preparation
performed no production neural forward, optimizer update, noise draw or RAW decode.

Also completed the previously missing full Tiny/Small natural-detail analysis
from saved FP32 predictions:427 photos/5124 cases/96,075 GT blocks. Weakest
ISO12800 gain is.36334/.36422 for V114/V115, with nearly unchanged band residuals.
Small's known-camera and analytic eight-pixel strengths support trying it as the
next parent; greater encoder capacity alone has not fixed weak natural detail.

Next is a full20k continuation from the fitted V115 final EMA, using the cleaned
90,791 Commons sources and this corrected, camera-balanced83-ID paired set.
Keep the band loss off, zero optical PSFs,4×→geometry→area2, existing low-contrast
photo attenuation and six reviewed ROIs. This tests a combined recipe plus
additional training, not an isolated dataset effect. Quality review follows the
full budget with native GT triplets and all six standing GFX crops.

[Sampler/data proof](../docs/paired-camera-sampling.md) ·
[Actual data receipt](../docs/results/paired83-camera-mask-reader-v1.json) ·
[Full Tiny/Small local detail](../docs/results/v114-v115-local-detail-v1.json).

