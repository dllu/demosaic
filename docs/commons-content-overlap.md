# Commons content-neighbor audit

A low-priority CPU job is screening all **85,048 training images** against the
**427 existing development photographs** for possible scene overlap beyond the
current dHash/correlation screen. The full screen is running. **No overlap
findings or clean-independence conclusion are claimed yet.**
[Executed pilot, source/dependency hashes, unit checks and actual launch](results/commons-content-overlap-CPU-launch.json).

The current split audit checks eight orientations, aspect ratio, dHash and
thumbnail correlation. Its documented limitation is arbitrary crops and changed
views. The new screen uses genuine frozen DINOv3 ConvNeXt-tiny content features
to retrieve candidates for manual review. Similarity alone does not establish a
shared scene, duplicate, leakage or a number of independent training scenes.

Each input comes from an existing linear uint16 8× cache on the SSD: center-square
crop, linear area reduction to 192×192, sRGB transfer and ImageNet normalization.
The pooled 768-vector is normalized to unit length. Every cache hash/header is
verified when read. Original JPEGs/RAFs, test caches and reserved camera captures
are not opened. The model is a content encoder; no image restoration or quality
scoring occurs.

The screen keeps three training memberships separate: original 40,170, active
expanded 66,934 and future 85,048. All are compared to the same 427 queries. F32
retrieval is followed by F64 cosine rescoring of 16 candidates per query/cohort;
three neighbors are retained. This does not claim exact all-F64 ranking. The
24 highest unique pairs will be rendered as scene thumbnails and reviewed before
any content or exclusion decision. One center view can miss other crops,
rotations or viewpoints. No split or active training recipe is changed.

The completed pilot processed 32 genuine images with 37 neural batches/72 image
evaluations. B1 and B8 features match bitwise; an exact B8 repeat also passes.
All 32 vectors are distinct, with independent F64 norms in [.999999908,1.000000132]
and off-diagonal cosines between −.07186 and .46429. The 16-image preprocessing
preview was actually viewed. These resized content thumbnails are separate from
the native 100% model-performance crops.

The actual backbone tensor hash matches the previously verified genuine DINO
used by our restoration model:
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
Model/revision:
`facebook/dinov3-convnext-tiny-pretrain-lvd1689m` /
`10d30274b4d445111e2d5bf75ac93bbd94db274b`.
There is no random fallback. Two focused tests verify center/linear/sRGB
preprocessing, read-only cache handling and independent all-pair F64 retrieval,
including similarity ties and three cohort memberships.

Runtime is CPU FP32/B8/two Torch threads, nice+10, with 24 GiB memory and 512 GiB
SSD reserves and an eight-hour bound. It has no automatic retry. The executed
driver, helper, dependencies, input identities and output vectors are archived
on the external SSD. At launch the actual owner is PID 82634/creation 1792241147.48.
Check actual process identity and status before acting; an observation timeout
does not mean the job stopped.

Status and output:
`/mnt/external/demosaic/benchmarks/commons-DINO-overlap-CPU-v1/`.
The first launcher failed before cache reads/model loading due to a status-helper
argument collision. That failed directory/log is preserved; the corrected v2
pilot completed before this full job launched. A test-only sibling-import-path
error was corrected separately. No criterion or similarity threshold was tuned.

After completion: independently check coverage, vector norms, source identities
and neighbor arithmetic, then view all 24 selected pairs. Potential matches in a
future-only corpus must be distinguished from active-model training membership.
Any revised data version will be separate from the frozen ongoing comparison.
