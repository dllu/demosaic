# Complete the expanded local and spatial training pair

Recorded: 2026-11-18T06:29:23-08:00 (America/Los_Angeles).

The local-only and spatial EMAs each completed 12,000 updates. Both used
24,000 distinct photos and 96,000 native crops from the expanded schedule.
An independent reread matched every source against its epoch index and every
scene record byte for byte. The workers reported 79.43 and 85.75 minutes of
training respectively. [Completed checkpoint and observation bindings](../docs/results/expanded-scene-12000-v2/training-completion.json).

Replayed the earlier 32-pair wire and gap intervention with both endpoints.
The aligned guide adds 0.081 percentage points at ISO400 versus a neutral
scene and lowers ISO6400 weak response. The retained native crops still
show faint wires poorly. [Spatial endpoint and intervention report](../docs/expanded-scene-spatial12k.md).

Both standing GFX families were viewed at native size with the matched
local-only EMA, 100k parent and V120. The spatial arm gains 0.01650 and
0.00442 dB on the two development conditions, with slightly higher gradient
error. Coarse crossings and smooth sky hold, and fine cab crossings remain
incomplete. [Main scene review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Matched native evidence](../docs/expanded-scene-spatial12k.md#matched-development-and-standing-gfx-review).

The broad CPU collector initially applied a fixed V120 digest to the 100k
control, then hit the older scene loader's equivalent parent check. The
corrected collector and refreshed loader use the declared checkpoint
bindings. The next preflight completed all three cases and launched the
fixed full collection. [Admission and failure receipts](../docs/results/expanded-scene-12000-v2/matched-primary-admission.json) ·
[PSNR history](../docs/performance-history.md).
