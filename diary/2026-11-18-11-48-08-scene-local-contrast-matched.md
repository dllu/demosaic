# Started matched localized-contrast training

Recorded: 2026-11-18T11:48:08-08:00 (America/Los_Angeles).

The four 2,400-update arms cross ordinary or localized-contrast scene data
with local-only or spatial conditioning. Each arm uses the same 4,800
distinct photographs from the 90,692-photo scene pool and starts from the
full-corpus 100k EMA. Both real CUDA preflights passed. The localized spatial
arm is training.

A held-out natural-photo probe freezes 64 sources, two physical noise priors,
and exact paired fine residuals and flat cores. On its eight-source pilot,
the existing spatial 12k checkpoint produces slightly less flat-core fine
variation with aligned context and slightly lower true fine response. The
high-noise native crops still show missing stone grain and masonry detail.
The pilot's pooled response is dominated by three source crops. Five native
boards and five triplets were inspected.

The 64-photo weak-detail evaluation, fixed 427-photo and known/unseen camera
panels, and both standing GFX reviews are queued for the new endpoints.
Training completion, numerical scores and inspection of the new native
results remain open. The previous spatial 12k EMA is the spatial result
covered today. [Report and evidence](../docs/scene-local-contrast-2400.md) ·
[PSNR history](../docs/performance-history.md) ·
[Main GFX comparison](../docs/gfx-qualitative.md) ·
[Fine cab mesh](../docs/gfx-green-mesh.md).
