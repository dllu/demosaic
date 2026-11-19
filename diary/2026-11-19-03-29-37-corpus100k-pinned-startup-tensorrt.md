# Faster Corpus 100k CUDA startup and TensorRT screen

Recorded: 2026-11-19T03:29:37-08:00 (America/Los_Angeles).


A pinned per-tensor upload after CPU channels-last formatting cuts Corpus 100k
CLI checkpoint setup from 52.59 to 2.52 s. Process-to-TIFF latency drops from
111.16 to 52.32 s on the shared GB10. The two full 102 MP TIFFs are byte
identical. Production CUDA inference uses this path and reports checkpoint
setup time. The allocation fallback and tiled output tests pass.

The TensorRT FP16 hidden trunk restores the full frame in 37.05 s versus
41.33–42.75 s eager FP16. It preserves the inspected native details and
changes 0.552 DN16 RGB16 RMS. Selective FP8 saves 1.44 s more and adds
8.42 DN16 mean quiet chroma RMS to the ISO6400 wire panel. One block's
two NVFP4 DINO projections run native FP4 GEMMs with no net speed gain.
The existing broad panels cover eager FP16.
[Measurements, crops and receipts](../docs/corpus100k-faster-inference.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine cab mesh](../docs/gfx-green-mesh.md).
