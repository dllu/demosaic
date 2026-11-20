# What context adds to noise conditioning for fine detail

Recorded: 2026-11-20T07:28:33-08:00 (America/Los_Angeles).

Replayed the Local 50k EMA on the same sensor samples at five
conditioning strengths. The full 0.65× branch drives flat fine RMS on
the independent transfer from 4.12 to 140.22 DN16. The observed green
residual incorrectly favors that branch at every sampled present
location, and a response-to-perturbation correction only partially
repairs the risk estimate.

The bounded luminance branch recovers 0.645 natural fine-response
points with a 0.220 DN16 increase in independent fine-increment error.
Whole-photo texture evidence adds 0.016 points over the local gate.
The exact wire gaps show more residual weak-direction structure.
This is an inference-only result on the existing checkpoint.
[Report and complete evidence](../docs/context-conditioned-detail.md) ·
[Fixed evaluation coverage](../docs/performance-history.md).

Viewed two exact present/flat pairs and both standing GFX families.
Reduced variance exposes more diagonals on the right cab and leaves
heavy artifacts. The bounded version keeps the sky smooth and fine
crossings incomplete.
[Main GFX views](../docs/gfx-qualitative.md) ·
[Fine mesh and JPEG references](../docs/gfx-green-mesh.md).
