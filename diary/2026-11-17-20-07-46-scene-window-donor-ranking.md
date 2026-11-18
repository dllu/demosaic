# Search localized RAW donor windows with full-frame context

Recorded: 2026-11-17T20:07:46-08:00 (America/Los_Angeles).

The donor catalog expands from fixed brackets to geometrically
valid pairs of native windows. Full-frame and near appearance pick
both intended frames on 6/8 ISO400 two-family queries. Spectral
ranking selects the stronger rotated distractors. Full-frame
recovers 4.80% faint response at the original scale compared with
9.02% for fixed brackets. Under the common quiet cap, all new
methods recover less than 1%. The path prior selects fewer windows
with a majority of matching material. Full-frame ranking rejects
all 12 fresh rail-only controls in the same-seed repeat.
[Report and measurements](../docs/scene-window-donors.md).

I inspected both native GFX families and the selected cab windows.
Full-frame appearance avoids the false building bands from the
wider spectral search. The near and full paths continue to choose
foliage and train body in the cab scene. Fine crossings remain
unresolved. [Main scene](../docs/gfx-qualitative.md) ·
[Fine green mesh](../docs/gfx-green-mesh.md).

The broader full-model schedule passed 65,250 updates. Its latest
reviewed checkpoint is 50k. The window study reuses both EMA
checkpoints and adds no PSNR history entries.
[Full-corpus review](../docs/full-corpus-scaling.md) ·
[Standard panel coverage](../docs/performance-history.md).
