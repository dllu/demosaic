# Corpus 100k overlap and inference fidelity

Recorded: 2026-11-19T16:56:41-08:00 (America/Los_Angeles).

The same Corpus 100k EMA used 512-pixel tiles, batch four, the established
nominal noise prior and cached DSCF3879. The paired full-frame tile loop
fell 16.53% from eager FP16 to TensorRT FP16 on the trunk and DINO at
overlap 64. Reducing the compiled overlap to 32 saved another 8.94%.
Both 64-pixel controls reproduced their archived TIFFs byte for byte.

The narrower grid changed bright lights and seams. Camera-RGB RMS
difference was 11.50 DN16 versus the compiled 64-pixel result, with a
9,716-code outlier on the train display. At ISO6400 the exact seam tests
showed 1.35 DN16 higher quiet chroma RMS and 0.49 DN16 higher gap luma
RMS. The main sky stayed smooth and the coarse fence retained its
crossings. The fine cab mesh used its fixed native ROIs on the actual
full-frame grids under both noise profiles. Incomplete crossings persisted
and the transferred right crop darkened slightly at overlap 32.

Keep the supported eager FP16 CLI at 512/64. The compiled fixed-grid
path remains a prototype. This is an inference study using existing EMA
weights. The PSNR history retains the existing comparable fixed-panel
measurements.

[Report and source-bound receipts](../docs/corpus100k-overlap.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine green mesh review map](../docs/gfx-green-mesh.md) ·
[PSNR history](../docs/performance-history.md).
