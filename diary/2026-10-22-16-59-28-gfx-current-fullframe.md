# Verify complete GFX exports and publish native full-frame comparisons

Recorded: 2026-10-22T16:59:28-07:00 (America/Los_Angeles).

The complete GFX3879 scene has been restored by V84/V100/V101 and RawNIND with CFA-channel input gain, using CUDA IEEE FP32, tile512/overlap64/B4, 520 tiles over 101.995852MP. All owners exited normally. Inference/blending times are 168.47/168.21/168.05/17.25s respectively; these exclude RAW decode, model loading and TIFF writes. No 10s-target claim or speed optimization.

Independently rehashed all eight complete TIFFs and reopened their 8746×11662×3 uint16 RGB headers/tags, including ICC profiles for the sRGB files. The writer's 33 sampled full-width rows per export differ from supplied floats by at most .5019368 normalized 16-bit DN. This is export/rounding validation, not a whole-image learned-precision bound. Outputs remain local under `/mnt/external/demosaic/v84-quality-fullframe-20261022-v1/`.

Published 24 unchanged native160 triplets and inspected all 36 unique cells on the six-region board, plus four resized whole-scene overviews for context only. Same noisy/reference pixels and transforms match exactly across methods. Native crops come from blended float restorations before RGB16 encoding, unlike the earlier independent 512px CPU contexts. Learned versions look close: cleaner mesh/rails than RawNIND, but foliage and illuminated-sign structure remain smooth. The independent ISO100 f/5.6 reference is not GT; aperture, capture time and moving/exposure-dependent subjects differ.

README and `docs/gfx-qualitative.md` now use the actual full-frame V101 foliage/fence crops and full-frame comparison, retaining the CPU context gallery and immutable earlier receipts as separate evidence. Public result: `docs/results/gfx-V84-V100-V101-fullframe-v1.json`; immutable private gallery/replay snapshot: `.cache/current-quality-20261022-v1/fullframe-publication-v1/`. Cached original RAFs remain read-only and scene/siblings remain outside training.
