# V66 completed: phase helps the matched warmup, quality remains poor

Finished the original1,000-update phase-conditioned RAW-head trial. All41 logged
inputs/domains/LRs match V65. Independent state inspection and the final artifact
audit verify94 model/94 EMA/three AdamW states, all finite; all91 original
restoration tensors remain bitwise V60. Source fc0297 and data/recipe/RNG are
verified. Training, primary, statistics/hue and artifact owners have exited.

Independently checked50,264 primary cases and48 saved comparisons/12 classical
witnesses. Photo29.52620/.872886, procedural28.02954/.864642; known/unseen
CFA45.95696/43.67401. Versus matched V65: photo+1.69373dB (source95% interval
[1.62423,1.75916]), procedural−.97537 ([−1.59974,−.33590]), known+1.73197 and
unseen+2.23102. V60 still leads photo by6.13809dB. No promotion; V43 remains
the working reference. One seed/finite budget, not convergence or causal proof
that frozen features explain the deficit.

Actually viewed all26 new native PNGs at original resolution. A tool response
containing the last three camera images was truncated; those three were explicitly
viewed again before receipt publication. Less noise than V65, but substantial
grain hides fabric, facade, foliage and fence detail. RawNIND is only a comparator;
separate ISO100/AHD GFX capture is not exact GT. The report includes two exact
simulated-GT photo triplets, all four standing GFX regions, one carrier and one
color triplet, copied unchanged. All source/ROI/noise/exposure/checkpoint records
are retained. README's representative V43 crops stay current.

The new1176-case hue grid has7056 independently checked Torch64 fields and216
group scalars. Source records match both retained V65 and V60; no legacy arrays
merged into the changed-source report. Means remain low-bias with high residual
noise. Analytic896 cases/56 groups/1504 summary fields audit successfully; no
unavailable full-array audit is claimed. Two full101.996MP RGB16 files and four
exact full-TIFF/native-ROI checks pass. Eighteen three-camera rerenders differ by
only one channel code at one pixel within the unchanged preview-only bound.
Shared-machine restoration/blending51.352s/peak5.614GB;10s target remains unmet.

Public report:
`docs/raw-kernel-phase-v66-first1k-review.md`, machine receipt
`docs/results/raw-kernel-phase-warmup-v66-first1k-review.json` SHA256
`1185226bdc2b46e3d49b8c57e44fbb92a4cbdb97b1f05051811327e01adab33f`.
All image hashes and local report links checked; git diff --check passes.

Next: separately declare and verify joint restoration training from completed
V66 EMA, keeping actual DINO and physical reconstruction fixed. This report
launches no stage. Existing head-only/1000-step/frozen91 audit gates cannot be
used as evidence for a joint stage with a different optimizer and budget.
