# Paired TensorRT FP16 timing on 520 GFX tiles

Recorded: 2026-11-19T08:58:26-08:00 (America/Los_Angeles).

Read the mixed-precision production notes and held the Corpus 100k EMA,
512-pixel tile grid, batch four and camera arithmetic fixed. Built two
static TensorRT FP16 engines with wider tactic searches. The short screens
changed their ranking between CUDA streams. After full restores showed
a wide spread on the shared GB10, interleaved the earlier engine and the
level-3 static engine with eager on every batch of the 102 MP GFX frame.
Summed forward times were 25.832 s eager, 22.631 s for the earlier engine
and 22.633 s for the static engine. The existing engine was faster than
eager on all 130 batches.
[Report](../docs/corpus100k-trt-tactics.md) ·
[Machine evidence](../docs/results/corpus100k-trt-tactics-v1/publication.json).

The four main crops, both fine cab crops with both priors, two exact-target
triplets and two RGB16 tail crops were reviewed at native size. The static
full export differs from IEEE FP32 by 0.541 DN16 RMS. The clipped cyclist
has a persistent yellow background shift across the renderings. The
rechecked 512-pixel weak-wire panel has small differences in fitted
response and quiet chroma. The 427-photo and camera panels published
earlier cover the existing TensorRT FP16 engine.
[Main camera review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Earlier fixed-panel comparison](../docs/corpus100k-fp16-throughput.md#tensorrt-fp16-on-the-fixed-panels).
