# Review the expanded local-only 12k endpoint

Recorded: 2026-11-18T05:08:05-08:00 (America/Los_Angeles).

The expanded local-only arm completed the fixed 12,000 updates in
4,765.53 seconds. I verified the EMA checkpoint, raw and EMA state
and the exact order of all 24,000 distinct photos and 96,000 native
examples. The scoped CPU collection used the existing fixed Bayer
observations and both matched controls. The shadows/ISO12800 sRGB
gains over 100k EMA are 0.09259/0.08775 dB.

I viewed both GFX families, including both cab priors and JPEGs. The
local 12k keeps a smooth sky and coherent coarse crossings. Thin cords and
the fine green grid remain incomplete. The matched spatial arm has started.
Its direct comparison and the three broad panels await both endpoints.
Corpus 20k remains the most recent completed three-panel candidate.

[Endpoint and native report](../docs/expanded-scene-local12k.md) ·
[Runnable matched recipe](../docs/expanded-scene-corpus.md#matched-12000-update-continuation) ·
[PSNR history](../docs/performance-history.md) ·
[Main GFX](../docs/gfx-qualitative.md) · [Fine cab mesh](../docs/gfx-green-mesh.md).
