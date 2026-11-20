# Train bounded detail gates with exterior context

Recorded: 2026-11-20T09:06:16-08:00 (America/Los_Angeles).

## Results

The matched local, pooled and aligned gain heads each finished
1,200 updates on statistics from 1,600 separate training photos.
The shared fit took 11.61 seconds after 1,194.03 seconds of
measured frozen feature collection. The heads preserve raw and EMA
weights. Exact natural targets and wires were scored using EMA.

On 32 held ISO6400 photos the aligned lock adds 0.189 contrast
points over Local 50k and 0.019 DN16 exact-flat RMS. It gains
0.085 points over the learned local lock. Using another photo's
scene features changes response 0.010 points. At matched response
the earlier Bayer rule has 0.033 DN16 lower flat RMS. Exact targets
have 2.418 points of remaining measured headroom in the same
proposal fields at lower paired and flat error.

All 12 standing GFX boards, the native exact triplets and the
flat companions were viewed. The coarse fence stays connected,
and fine cab crossings remain incomplete. The direct delivery
audit remeasures the locked outputs. All 27 focused scene tests
passed. Local DINO reuse gives exact RGB on the eight checked
batches and reduces the isolated median three-setting time from
524 to 495 ms.

This is a trained crop-scale component. The [full-model performance chart](../docs/performance-history.md)
tracks the comparable underlying full-model panels.

[Report](../docs/scene-detail-selector.md) ·
[Main scene review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md) ·
[Checkpoint and receipt hashes](../docs/results/scene-detail-selector-v1/publication.json).
