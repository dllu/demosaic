# Matched V95 palette stages completed; full quality evaluation

Recorded: 2026-10-21T17:42:52-07:00 (America/Los_Angeles).

V97 completes4,000 updates and its final validation/checkpoint, then exits.
The matched controller records both completed arms and exits. Confirm both
actual worker/controller identities are absent before preparing evaluation.
Each arm has4,000 optimizer/training forwards,128 validation forwards and
4,128 actual DINO calls. Both final frozen-DINO/no-gradient checks pass.
Together the completed production stages have8,000 updates/256 validation
forwards/8,256 DINO calls, separate from the discarded96 preflight updates.

Run the independent CPU-only V97 saved-state auditor. All five retained
model/EMA/Adam states, exact V95 lineage/architecture,161 finite logged
loss/gradient rows, four scheduled28-cell×8-source validations, manifests,
source/protocol and first24 inputs versus its actual CUDA proof pass.
Audit SHA `9088802a87e870da087109307330a868a31c6db381d04edeeb3220d71653c289`;
[published V97 audit](../docs/results/v95-palette-V97-completed-training-v1.json)
SHA `9ccadb1bf83e0baf9b687e4c061ea0e9d77816365d4b2d78ea82b967b21d9ee0`.
Final4k SHA `1ab0b6a3d2e30260eb41eeb11a7990ef55b15bbfec9dbfa4257e091b2f47ce27`.
V96/V97 validation-best steps3k/2k remain diagnostic; final4k is primary.

Independently reconstruct the matched logged-input comparison:69 native/paired
observations are identical,58 affected Commons observations differ. Each
production first24 trace exactly matches its own CUDA proof. Numerical source
remains `ea9622343d2ad4d9f12ea0089884ad9dcefb87be4ae06f24eacc764829c02d09`.
Completed training status SHA
`ddc961ce8efb02ea810685c083beac52f7941e97559bdacae4aed61b72f85138`.

Freeze the full V43/V95/V96/V97 evaluation in fresh local/external namespaces:
`.cache/quality-first-20261020/V95-palette-matched-evaluation-v1/` and
`/mnt/external/demosaic/v95-palette-evaluation-20261021-v1/`.
Plan SHA `559e3fb7fac99f6fc5aaf27f1f98d5cc252dc1ca4692d3278ca8c9dafaadfd27`;
1,796 inputs and64 frozen files. Pin actual per-checkpoint stage/initializer
lineage and all seven reviewed V43/V95 reference witnesses. Fresh IEEE FP32,
native256/B4,427 photos+16 procedural/7 conditions/4 CFAs/9 methods, followed
serially by known/unseen,carrier/flat,color,GFX and highlight stages. Original
resource floors and bounded same-worker disk-pause policy remain unchanged.

Launch once after actual training-owner exit and successful frozen-input guards.
Evaluation controller PID3905899/create1792629846.25; actual photo worker
PID3906010/create1792629910.88. The photo worker advances through8, then16,
32 and40 sources, with real score rows and native crop files. No saved
predictions are reused. [Completed training/full evaluation launch receipt](../docs/results/v95-palette-completed-training-and-evaluation-launch-v1.json)
SHA `ce4ff8c920039aac56079f626d4e5d5d25b721e7fa1f5586d526d3fde4156353`.

Snapshot and actually view all12 preselected photo triplets in one original-size
board:16 distinct native160 cells after sharing noisy/reference panels. Also
view original V96 fabric and both V97 triplets directly. V97 shows a visible
green/olive fabric cast and uneven tone versus exact GT and the other endpoints.
All four lose much of the fine suspension-line structure; V96 also has some
uneven fabric tone. Building geometry is clearer in the joint models than the
two viewed RawNIND adapters, but fine cloud texture is smoothed and joint-model
differences are modest. These two fixed photos do not establish a broad winner.

Publish eight byte-exact native triplets/two per joint model with original
sidecars, source/ROI/checkpoint/noise/display metadata and attribution in the
[quality review in progress](../docs/v95-flat-palette-quality-review.md).
[Actual viewing/publication receipt](../docs/results/v95-palette-first-native-photo-review-v1.json)
SHA `3186ebbf4a2cc125aa21a8f158f7684e361f841e479fed9bd64f2d713f3728dc`.
The negative V97 example remains; do not select a different crop or substitute
validation-best weights. Full means/uncertainty, final invariant/reference
checks and camera/analytic/color/GFX/native review are still pending. V43 stays
working reference and speed stays deferred. The full PROMPT goal is not complete.

