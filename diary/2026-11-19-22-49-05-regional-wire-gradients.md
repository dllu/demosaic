# Measure shared gradients for weak-wire training

Recorded: 2026-11-19T22:49:05-08:00 (America/Los_Angeles).

Measured the individual wire gradients on 32 balanced groups from the
fixed continuation schedule at the Local 50k starting checkpoint.
Output orthogonality to the exact-flat and strong-gap controls did
not survive backpropagation through the shared weights. Both weak
losses often oppose the flat and weak-absence controls. The regional
gradient is usually weaker than the whole-core term after the
initial matching on output gradients.
[Audit and per-source evidence](../docs/local-regional-wire-gradient-audit.md).

Both matched 512-update checkpoints passed raw/EMA and AdamW
state checks. The next scoped replay runs on the frozen exact, off-grid
and standing GFX inputs, reusing the Local 50k arrays by hash.
The [128-update checkpoint review](../docs/local-regional-wire-128.md)
remains the latest completed image comparison. [PSNR history](../docs/performance-history.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine green mesh review map](../docs/gfx-green-mesh.md).
