# Test the gain headroom of the scene spectral correction

Recorded: 2026-11-17T16:33:57-08:00 (America/Los_Angeles).

The spatial spectral head replays all 134 learned outputs bit for bit. I
sealed the longer and finer corrections with the original support held
fixed before scoring the production observations. A leave-source-out fit
chooses the upper gain bound of 2 for both bands in all 64 folds. It
improves mean rendered PSNR by about 0.0016 dB and raises fine weak-band
and measured quiet-region error. Keeping only the longer correction has
a small longer-band benefit with near-parent quiet error.

An exact-target local fit in every eligible ISO12800 block reduces fine
error from 215.18 to 214.82 DN16 within the gain cap. After the held-out
fits saturated, I also measured the unbounded local limit. Nonnegative
gains reach 212.90 DN16, about 1.1% better than V120, and signed gains
reach 210.28 DN16. These fits use the same two measured bands with frozen
support. Both GFX scenes were viewed, and fine cab crossings remain
incomplete. V120 remains the recommendation.

[Fixed-gain tests, exact targets and native crops](../docs/scene-spectral-gain-headroom.md) ·
[Main GFX comparison](../docs/gfx-qualitative.md) ·
[Cab comparison](../docs/gfx-green-mesh.md) ·
[Standard PSNR history](../docs/performance-history.md).
