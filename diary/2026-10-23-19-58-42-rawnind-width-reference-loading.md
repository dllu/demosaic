# Compare released RawNIND width variants and enable standard loading

Recorded: 2026-10-23T19:58:42-07:00 (America/Los_Angeles).

The genuine publisher width48 UtNet2 (iteration 5,985,000, checkpoint SHA256
`a13db60df69de2e107a9470bd419dbcc1bb4861f37e7127159f7ed774dc4ea99`)
finished the same fixed photographic diagnostic, adverse camera crops, six
GFX contexts and all 162 known/unseen camera development crops. Only 189 new
scientific network forwards were needed; the exact earlier controls were reused.

Width48 reaches 53.98802/53.66548 dB on the known/unseen panels, below both
width32 references and −.27265/−.19980 dB behind pre-upsampled. All nine scene
means decline relative to half; eight decline relative to pre-upsampled.
All three photo condition means also decline. Its separate training history
prevents interpreting this as a controlled width ablation. Keep pre-upsampled
as the strongest of these three tested RawNIND references; broad real-camera
superiority for our models remains unproven.

Independent audits rebuild 554 joined reference primary rows and 1,656 gain
normal equations, including reused controls and overlapping pilot/full cases.
All 126 native panels reconstruct exactly. All 62 distinct board cells were
actually viewed: width48 bark/fur remain soft and coarse; GFX mesh remains
moire-prone and blue-sign grid/grain is more conspicuous than pre-upsampled.
V104 retains more coherent mesh/building structure but still misses fine
foliage/hair and saturated-sign detail. ISO100/AHD are not exact RGB GT.
[Current three-variant comparisons](../docs/rawnind-variants.md) include all
42 native triplets and [bound evidence](../docs/results/rawnind-three-variants-current-v1.json).

The public loader now infers the tested checkpoint geometries and strictly
loads all tensors; the fetcher supports pinned half/preupsample/wide48 variants.
Receipts identify the detected configuration. Three genuine native256 output
replays are byte-exact, cache reuse needs no network and legacy constructor
RNG/state is unchanged. Focused loader/CFA/calibration/reporting tests pass.
An exception-type lint correction was made after the initial successful replay;
both validation source snapshots and results are retained, with final parity
checked again after the correction. Earlier machine receipts are untouched.

The complete `feat/linear-dng-export` tip `4381fc23` is already an ancestor of
main through merge `12f0810`; hot-pixel removal and linear DNG support require
no additional merge. V104 stays active while the owned V111/V112 loss-scale
trials continue on the cleaned corpus. Their frozen sources/plans and queued
quality evaluations are unaffected.

