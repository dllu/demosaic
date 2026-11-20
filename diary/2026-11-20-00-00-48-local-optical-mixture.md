# Launch matched mixed-optics training

Recorded: 2026-11-20T00:00:48-08:00 (America/Los_Angeles).

Launched a fresh Local 50k continuation against the existing regional
EMA's same 1,024 ordered source groups and optimizer schedule. The
mixed arm keeps 512 groups sharp and filters 256 groups at each of
σ 0.40 and 0.65 native pixels before camera simulation. It reconstructs
the clean image as seen through the simulated optics.

Eight qualification updates passed. Forty-eight reconstructed sharp
input groups matched their archived bytes, and the first actual
training step matched the archived sharp control's losses and
gradient norm. Verified the first 60 logged updates against the
scheduled optical widths. Froze 24 separate photo backgrounds and
72 captures covering σ 0, 0.55 and 0.85 before the run began. Scoped
quality, the standing GFX comparisons and the canonical panels await
the trained endpoint.

[Training plan and review](../docs/local-optical-mixture.md) ·
[Launch receipt](../docs/results/local-optical-mixture-v1/launch.json).
