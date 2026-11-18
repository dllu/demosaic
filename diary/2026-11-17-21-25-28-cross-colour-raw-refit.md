# Cross-color evidence for screened RAW refits

Recorded: 2026-11-17T21:25:28-08:00 (America/Los_Angeles).

Kept the discovery-only rail background, whole-frame guide frequencies and
per-color weighted refit fixed. Compared the independent gate, a joint CFA
gate, and bounded evidence from the other two colors. The bounded gate
raises quiet-capped ISO400 response modestly on ordinary wires. Both pooled
gates increase false correction on complex rails at the nominal threshold.
Even with exact frequency and an analytic rail parent, ISO6400 weak response
stays near zero and weak-increment RMS rises with both pooled gates.

The numerical replay and native review are complete. The main sky is exact
to V120, the coarse fence keeps its crossings and both cab ROIs remain at
their conditioned V120 pixels for both profiles. Existing AHD and camera
JPEG references were used at the fixed coordinates. No model was trained.
The independent gate stays the component baseline and V120 stays the
general recommendation. The gate study leaves the
[full-model score history](../docs/performance-history.md) unchanged.
[Report and crops](../docs/cross-colour-refit.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Cab review map](../docs/gfx-green-mesh.md).

The first rail replay found an import missing from the frozen snapshot.
The retry used the already-hashed module from the screened-background
study. Both logs are preserved, and new snapshots include the dependency.
All 127 focused tests passed.
[Executed evidence](../docs/results/cross-colour-refit-v1/publication.json).
