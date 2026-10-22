# V96 final4k training completed and audited

Recorded: 2026-10-21T17:09:30-07:00 (America/Los_Angeles).

The actual V96 worker PID3845032/create1792625778.91 completes all4,000
updates and exits. The frozen controller advances to V97, waiting for the
original resource thresholds before launching that same planned treatment.
V96 counts:4,000 training/optimizer steps,128 validation forwards and4,128
actual DINO calls. Frozen DINO weights/no-gradient assertions complete.

Run the independent CPU-only saved-state auditor with CUDA hidden. All five
retained checkpoints pass:step1k/2k/3k,final4k and validation-best3k. Each has
71 finite model tensors,71 finite EMA tensors and69 finite Adam states at
its actual checkpoint step. Effective architecture, full V95 initializer
path/hash/step, source/manifests/protocol and expected configuration are exact.
All161 logged loss/gradient rows are finite; all four scheduled validations
cover8 sources×28 condition/CFA cells,224 observations per validation. First24
production inputs exactly match V96's actual discarded CUDA preflight.

Primary final4k checkpoint SHA
`c3754741e210ece42093064bf8f95035c7735e79a82541b6edac83c24a510c0f`.
Metrics SHA `ac3144031fdc0c8c9b9993e1aa6e434029dc303adf8ce86b20c330303a122818`.
Independent audit SHA `662ab49604b17ce30f9da234c87dde6af634f31861f4acc5ca8b571728fcc1f2`.
Publish the [completed training audit](../docs/results/v95-palette-V96-completed-training-v1.json),
SHA `3523d9b61201d87e356b3d5ec6de386ac960f6640382ea0e7c56cc6072047985`.
The numerical package remains
`ea9622343d2ad4d9f12ea0089884ad9dcefb87be4ae06f24eacc764829c02d09`.
Validation-best is diagnostic; do not select it instead of the fixed final4k
primary endpoint or interpret its small training panel as held-out quality.

Observe actual V97 production PID3898810/create1792627778.69 at step50 with
finite loss/gradient, under the original controller
PID3838388/create1792625353.89. Resource readings remain above the original
floors. V97's completion and the matched cross-arm observation audit remain
pending, followed by full fresh FP32 primary/analytic/color/GFX/native review.
V43 stays working reference; no quality or speed promotion follows from these
training checks. The full PROMPT objective remains active.

