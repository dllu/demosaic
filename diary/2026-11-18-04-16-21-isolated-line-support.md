# Local Bayer support for isolated line continuation

Recorded: 2026-11-18T04:16:21-08:00 (America/Los_Angeles).

The earlier whole-scene EMA gave almost the same weak response with
aligned and orthogonal exterior cues. The explicit RAW follow-up
estimates one isolated line outside the query, then fits the candidate
with two disjoint sets of native Bayer measurements. The initial
ISO400 continuous test gains 12.24% to 92.85% response with the whole
fit. Inside a partial gap, that fit adds about 76 DN16 RMS of structure.
The fresh geometry and noise panel retains 80.58% response with
the shorter support check, and added gap RMS falls from 8.70 to
2.40 DN16 versus the 64-pixel estimate alone. Some real segments at
gap boundaries remain weak. ISO6400 gains are much smaller.

The packaged experimental API reproduces 24 retained prototype
predictions exactly and falls back to the local parent in all eight
standing GFX views. Both references and both cab noise profiles remain
in the native boards. Forty-six focused tests pass after fixing the
random initialization of one existing scene test fixture.
[Method and native crops](../docs/isolated-raw-line.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Cab GFX map](../docs/gfx-green-mesh.md).

The 12k scene experiment continues with its first local-only arm.
The analytic component study supplies scoped synthetic metrics.
[Expanded scene training](../docs/expanded-scene-corpus.md#matched-12000-update-continuation) ·
[Comparable PSNR history](../docs/performance-history.md).
