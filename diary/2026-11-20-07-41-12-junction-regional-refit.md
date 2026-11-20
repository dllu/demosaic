# Refitting held Bayer junction contrast after the first pass

Recorded: 2026-11-20T07:41:12-08:00 (America/Los_Angeles).

Projected the lower-noise Local 50k output onto the existing
Bayer-confirmed difference band. On 24 new exact-target junction
backgrounds the RAW-only remeasurement recovers 0.724 contrast
points with 0.216 DN16 lower junction error and 0.015 DN16 added
gap luma. The projected neural branch gives nearly the same
junction error at matched contrast, with an additional forward.
Repeating the wider Bayer pass recovers more contrast and leaves
somewhat larger gap residuals.

Added the optional crop mode `weak-junction-refit` after confirming
bit-for-bit research parity on 344 crops and all 97 focused tests.
Affected crops take 107.8 ms median versus 87.5 ms after the parent
forward. No training was run. [Report and evidence](../docs/junction-regional-refit.md) ·
[Fixed benchmark coverage](../docs/performance-history.md).

Viewed two exact-target scenes and both standing GFX families. The
right cab gains subtle crossing modulation and incomplete intersections
remain. [Main GFX views](../docs/gfx-qualitative.md) ·
[Fine mesh views and JPEG references](../docs/gfx-green-mesh.md).
