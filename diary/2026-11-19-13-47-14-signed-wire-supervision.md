# Identify the continuing wire loss inside exact gaps

Recorded: 2026-11-19T13:47:14-08:00 (America/Los_Angeles).

All three 320-update full local trunk continuations start from the
repeat-loss EMA and see the same 1,920 observations per arm. Training
lasted 1,067.96 s. The clean-increment loss gains 1.26 points of recovered
weak response over the repeat control across separate redrawn wire
fields, with 2.9% more draw-dependent variance. Flat and weak-direction
gap RMS are nearly the same. [Training and held-out review](../docs/local-wire-response.md).

The gap error against the starting model comes mainly from the loss of
the continuing strong direction. Across 12 exact gaps its target-aligned
response falls 9.24 points. The weak-direction residual is slightly
smaller. I viewed the exact crops and both GFX scenes at native scale.
The aligned arm keeps the sky smooth and the coarse crossings coherent.
Fine cab crossings remain incomplete under both noise profiles.
[Gap decomposition](../docs/local-wire-response.md#which-detail-is-lost-inside-the-gaps) ·
[Main scene map](../docs/gfx-qualitative.md) · [Cab map](../docs/gfx-green-mesh.md).

The candidate camera replay is running. The fixed photo replay follows
it. [Fixed panel status](../docs/local-wire-response.md#fixed-camera-panels) ·
[PSNR history](../docs/performance-history.md).
