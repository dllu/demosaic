# Train and review matched scene spectral gain

Recorded: 2026-11-17T16:17:49-08:00 (America/Los_Angeles).

The two spectral heads each completed 800 updates from the same 791
distinct source photos and 3,200 native crop examples. Both heads use
the frozen V120 EMA reconstruction and native spectral innovation.
Pooled and aligned scene features have the same architecture and
supervision. The raw and EMA weights are bound to the 381.43-second
shared run. The training audit rederives all 800 source draws and
verifies the endpoint state and validation split.

Both heads improve the longer weak band slightly across the 64-source
development review. Fine weak-band and quiet errors rise, and shifting
the aligned scene features makes negligible changes. I viewed the 16
native boards, including both GFX scenes and both green cab profiles.
Sky stays smooth, and the fine cab crossings and canopy cords remain
soft. V120 remains the recommendation. The first summary divided by
roundoff in nearly zero quiet bands. The corrected summary retains
quiet RMS and preserves the original reduction and prediction artifacts.

[Checkpoint, scores and native review](../docs/scene-spectral-detail.md) ·
[Main GFX comparison](../docs/gfx-qualitative.md) ·
[Cab comparison](../docs/gfx-green-mesh.md) ·
[Standard PSNR history](../docs/performance-history.md).
