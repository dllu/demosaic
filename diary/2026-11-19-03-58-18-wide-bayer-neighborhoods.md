# Wider Bayer phase neighborhoods and 60,000 local training photos

Recorded: 2026-11-19T03:58:18-08:00 (America/Los_Angeles).


Eight disjoint Bayer donors raise weak-phase accuracy and validated intact
matches in the ISO6400 panel. The head's unscaled response rises by 0.82
points and intact weak-band RMS falls by 0.85 DN16. With similar added gap
RMS, the response gain is 0.09 points and absolute gap RMS rises 0.34 DN16.
The agreement-based variant lowers intact weak-band RMS with an uncertain
gap error difference. Both real-scene families and exact target crops were
viewed. Existing right-cab diagonals strengthen and crossings stay incomplete.
[Study and exact crops](../docs/wide-bayer-neighborhood.md) ·
[Main scene](../docs/gfx-qualitative.md) ·
[Fine cab mesh](../docs/gfx-green-mesh.md).

Local-only continuation has verified 30,000 updates and 60,000 distinct
photos. Paired training is verified through 27,500 and 55,000 photos per arm.
The 30k exact-photo and standing review waits on the matched spatial
checkpoint. It verifies the saved FP32 control identities and input hashes
before reuse. Fixed427 and camera evaluations remain queued at 50k.
[Matched training coverage](../docs/scene-full-epoch.md#execution-status) ·
[Last complete quality review](../docs/scene-full-epoch-25k.md) ·
[Comparable PSNR history](../docs/performance-history.md).
