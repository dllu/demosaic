# Confirm weak-wire colour on reserved Bayer samples

Recorded: 2026-11-18T22:27:59-08:00 (America/Los_Angeles).

The held Bayer colour path fits signed per-colour amplitudes on the
weaker measured carrier. It tests their fixed chroma direction in Q2
and Q3 and delivers the correction in the luma-null subspace. Across
16 coloured ISO6400 fields, aligned response rises 34.40% → 38.74% and
intact chroma-increment RMS falls 143.58 → 142.12 DN16. The 48 prior
neutral replays and sixteen neutral observations from this panel all
preserve the base exactly. The eight GFX results also reproduce it.

The new edit still enters some real gaps in the constructed targets.
At equal intact response, the earlier RAW-confirmed gap taper lowers
mean added gap colour from 4.26 to 3.22 DN16 on the eight coloured
ISO6400 gaps in a retrospective replay. A score-only check supplies
exact frequency pairs and confirms three of the five missed high-noise
colour fields. It leaves both remaining misses and the neutral set quiet.
Both exact triplets and all standing comparisons were viewed. The
49 targeted tests pass. This is a scoped replay without broad PSNR.
[Report and native crops](../docs/query-signed-colour.md) ·
[Main camera map](../docs/gfx-qualitative.md) ·
[Fine green fence map](../docs/gfx-green-mesh.md) ·
[Comparable score history](../docs/performance-history.md).

The first spatial worker at the 13,500 boundary stalled in startup with
no training trace. Its I/O counters remained fixed while CPU time rose.
The replacement controller resumed from the verified 13,000 spatial
checkpoint on the original schedule. The completed 13,500 trace is
identical to local-only and covers 27,000 photos and 108,000 queries per
arm. The spatial worker continues toward 15k. The exact and standing
15k collectors remain live and wait for the matching checkpoint pair.
[Training and recovery evidence](../docs/scene-full-epoch.md#execution-status) ·
[Matching 13,500 source trace](../docs/results/scene-full-epoch-v1/paired-prefix-013500.json).
