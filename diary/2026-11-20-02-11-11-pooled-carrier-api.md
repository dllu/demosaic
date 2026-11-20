# Package the verified weaker carrier correction

Recorded: 2026-11-20T02:11:11-08:00 (America/Los_Angeles).

Packaged the weak-only refinement as an opt-in native crop method.
Vectorizing both held-green folds, reading just the sampled RAW footprint,
and keeping large pixel arrays out of the linear solve reproduces all
40,550,400 RGB values across 528 archived crops bit for bit.

The coarse fence and right cab take 37–38 ms per crop including donor
nomination and fitting, down from 70–71 ms for the archive implementation
in an interleaved one-thread CPU benchmark. The original planar crop
method takes 15–16 ms on those crops and remains the default. The native
comparisons reproduce the earlier result, including incomplete fine cab
crossings. This was an inference integration with the same Local 50k EMA.

[Usage](../docs/usage.md#repeating-mesh-crops) ·
[Replay and timing](../docs/local-pooled-carrier.md#packaged-crop-fit) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).
