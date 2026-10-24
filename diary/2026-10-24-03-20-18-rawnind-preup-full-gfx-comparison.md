# Compare the stronger RawNIND reference on the complete GFX frame

Recorded: 2026-10-24T03:20:18-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress by executing the fitted Small
CPU optimizer check and launching the V113 CUDA/training queue. This turn
revalidated the exact live existing GPU owners before doing independent CPU
work. Full V111/V112 photo evaluation completed while that work ran; its
separate scalar/source review does not require new neural inference.

The stronger pre-upsampled RawNIND had complete camera scores but only512-pixel
GFX contexts. I restored the complete cached DSCF3879 scene with that original
released checkpoint, CFA-channel input-only calibration, CPU IEEE FP32,
tile512/overlap64/B4. The actual counters recorded520 tiles,130 adapter calls
and520 upstream network calls, with zero joint-model forwards/CUDA/training.
Frozen reference weights stayed unchanged. Only locally cached RAFs were read.
The full restoration took263.04s under shared-machine conditions.

Both complete linear/sRGB RGB16 TIFFs were hashed and reopened as
8746×11662×3 uint16. Six original full-frame float ROIs are retained; all460,800
native linear16 channel samples match their declared float quantization exactly.

I actually viewed all30 native cells comparing noisy, V104, half RawNIND,
pre-upsampled RawNIND and the separate ISO100 reference. Pre-upsampled has
less periodic blue-sign texture than half. V104 retains thinner, more regular
fence wires; both references have coarser/beaded mesh. Fine foliage remains soft
across methods. Saturated display/motion and the different-aperture ISO100
capture still limit interpretation; no GFX pixelwise score or broad superiority
claim follows.

The first renderer rejected one shared sky-noise channel differing by1DN8
between CPU and earlier CUDA previews. All12 underlying noisy/reference float
arrays were verified bit-exact. A second renderer uses one common CPU preview
across methods, changing that one noisy channel in each of the two older
derived sky triplets. Every restored crop stays pixel-exact to its original
PNG, without resizing. Original reports, triplets, first renderer/failure and
all new source/ROI/display hashes remain preserved. No neural work was repeated.

[Current report](../docs/rawnind-fullframe.md) includes two full-frame
foliage/fence triplets and the six-region board. The GFX and reference guides
now link it. [Public receipt](../docs/results/rawnind-preupsample-full-GFX-review-v1.json),
SHA256 `4a3308bd02af4b8a0e83db1bec9d32da1b05a614ce777f9797b51d4b1c8ab219`.
The broader quality objective and V113 training remain active.
