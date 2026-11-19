# Test whole-image Bayer summaries as a weak-detail strength prior

Recorded: 2026-11-18T16:45:18-08:00 (America/Los_Angeles).

Tested a noise-debiased whole-image RAW power prior for scaling the
fixed native luma lift. Correct context lowers gain in the standing
sky and raises it in the coarse fence. Matched, mirrored and local-only
controls give nearly identical fine-increment RMS at similar response.
An exact-target blockwise fit reduces independent ISO6400 pooled RMS
from 147.471 to 147.173 DN16 at matched response and flat error.
Inspected three exact-target boards and both standing GFX families.
Fine cab crossings remain incomplete.
[Comparison and evidence](../docs/context-strength.md).

