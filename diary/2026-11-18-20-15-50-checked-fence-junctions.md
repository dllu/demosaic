# Check higher-order Bayer bands on the standing fence

Recorded: 2026-11-18T20:15:50-08:00 (America/Los_Angeles).

The standing right-cab crop already has two verified Bayer directions.
The exterior fallback bypasses that case. This test used those phases to
nominate second harmonics and crossing terms and required corroboration
from two reserved green groups. Both right noise profiles support a second
harmonic and difference band. A 90° phase rotation falls below the threshold
in each case. Some right crossings are slightly clearer, while mottling and
missing crossings remain. The sky, foliage, building and both left-cab
profiles match the previous reconstruction pixel for pixel.

On 27 separate exact-target backgrounds, phase locking adds 14.93 points of
aligned interaction response and 16.11 points for harmonics over the preceding
wide fit. The most affected null group adds 0.100 DN16 mean luma RMS. The
original 100k model still has slightly smaller increment RMS. All sixteen
final boards were viewed. The report includes the two exact triplets and the
archived initial run failures. This component had no training or primary
PSNR panels.
[Report and evidence](../docs/query-checked-junctions.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine green mesh](../docs/gfx-green-mesh.md) ·
[Comparable panel history](../docs/performance-history.md).

Full-epoch training verifies matching inputs in both arms through 8,000
updates on 16,000 distinct photos and 64,000 native queries per arm.
The local 10k checkpoint covers 20,000 distinct photos and 80,000 native
queries. The spatial worker automatically restarted from 8,000 when its
next segment reached the RAM reserve. The latest complete matched
numerical and native review is at 7,500.
[Training, audit and retry](../docs/scene-full-epoch.md#execution-status) ·
[7,500 quality review](../docs/scene-full-epoch.md#matched-quality-comparison-at-7500-updates).
