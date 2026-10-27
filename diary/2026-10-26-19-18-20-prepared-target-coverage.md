# Measure faint-detail coverage in actual prepared training targets

Recorded: 2026-10-26T19:18:20-07:00 (America/Los_Angeles).

Measured fine-band target coverage in actual retained V124 CUDA implementation
checks, rather than assuming the faint-detail failures indicate an empty
training contrast range. The prospective plan freezes all18 prepared archives,
configuration, source-choice code and four existing diagnostic targets. Counted
288 clean context slots once, excluding272 second-noise-view copies:176 Commons,
96 native and16 paired contexts. No clean target, noise or model inference is
regenerated.

The same central native160/DCT16 band as the conditional-noise diagnostic yields
16,667 eligible blocks from28,800 total. Ordinary photographic draws have7,014
eligible blocks,18.25% below2% contrast and31.19% below5%; seven reviewed-material
draws have615 blocks,22.76%/44.88%. Native targets have6,317 blocks,14.80%/23.63%.
The32 weak-procedural slots contribute1,400 eligible blocks, all below5%.
Two smooth-field slots also contribute125 eligible blocks, showing why this
energy statistic cannot itself certify useful physical texture.

Actually viewed six native160 prepared targets selected by weak-block counts:
four ordinary and two reviewed photographic regions. Several ordinary targets
are dominated by flat surfaces or soft backgrounds. The fishing net retains
faint repeated strands and the misty reeds remain coherent soft scene structure.
These are target-only views with actual WB/matrix and exposure1, not a denoised
quality comparison. Crop pixels are never resized. Counts do not establish
noiseless material, sufficiency, corpus prevalence or a better sampling policy.

Independent verification uses an even-extension FFT rather than the analyzer's
cosine matrices for all28,800 DCT blocks. Every eligible mask/bin and all288
per-context count rows match. Maximum band-RMS difference is5.8621e-16; maximum
eligible relative-RMS difference is1.9984e-15. Original frozen reader methods,
AST-specialized to stop before photo-cache access, reproduce all176 Commons
family/source selections. All16 actual trace rows match. The four reference
histograms match all32 prior model/CFA conditional-response groups exactly.
Independent explicit-channel display arithmetic reproduces all460,800 native
image channels and their board placements exactly. Ten focused tests and Ruff
pass. Source code, plan, arrays, plots and receipts remain retained locally.

Published the stacked contrast plot, six viewed target cells, complete context
CSV, source credits and a focused report. The first plot's legend overlapped
its top-panel title; preserved that source/output and separately rendered/viewed
v2 with layout-only changes. No target analysis or model is repeated for this
chart correction.

Primary Commons attribution review clarified that the bust's frozen author
field describes sculptor David d'Angers, while its source field credits
photographer Selbymay. Preserved source rows, original credits CSV and receipt;
added corrected photograph credits and a separate clarification receipt backed
by an immutable MediaWiki revision snapshot. Also corrected the README fur
credit to CC BY3.0, as already recorded in its immutable image metadata.

Refreshed stale current documentation: V120 remains the general recommendation,
V114 remains a useful Tiny/matched-study control, the V118 band term stays off
after its completed adverse comparison, and the current selector now describes
the completed matched-Haar full-frame review. Preserved the previous selector
bytes. All twelve active/queued plans were inspected; none binds the mutable
public selector. Checkpoint, architecture and preferred version are unchanged.
Training-pipeline docs now distinguish active90786/14, queued90784/20 and the
separate untrained90783/20 future cohort.

Keep all current/queued sampling, blur and loss settings fixed. Faint-band
support is present, but future additions need actual material inspection rather
than merely maximizing weak-band counts. Shadows below.02, clipped regions,
other frequencies and the full training distribution remain unmeasured here.
V123 reached update6,675 at the latest logged check and continues its original
budget. No new neural/encoder call, sensor observation, source-cache image read,
RAW decode, optimizer update or active/queued training change is added.

[Target-coverage report](../docs/training-target-contrast-coverage.md) ·
[Complete measurement and verification](../docs/results/training-target-coverage-v1.json) ·
[Attribution clarification](../docs/results/training-target-coverage-publication-v1.json) ·
[Current-selector documentation refresh](../docs/results/current-model-gfx-doc-refresh-v1.json).
