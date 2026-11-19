# Measure repeat and exact-gap losses on weak detail

Recorded: 2026-11-19T13:05:54-08:00 (America/Los_Angeles).

The three full local continuation arms start from the mean-redraw EMA
and see the same 320 source photos and two independent redraws. The full
training loop took 730.85 s. The hashes and separate EMA and raw states
are recorded in the report. [Matched training](../docs/local-redraw-stability.md#matched-training).

Repeat loss cuts independent draw-sensitive variance by 20.2% and
fine-increment error by 2.83 DN16 on the held-out natural panels. The
extra stability comes with weaker recovered detail. At equal natural
response to an earlier output mixture, exact-flat fine RMS remains
0.28 DN16 lower. Adding exact-gap supervision recovers 0.66 weak-wire
points over repeat and increases wire flat RMS. [Source-level comparison](../docs/local-redraw-stability.md).

I viewed the unchanged crop pixels on the exact targets and both
standing GFX100S scenes, including both cab profiles and camera JPEGs.
The overcast sky remains smooth and coarse crossings remain coherent.
The fine cab lattice stays incomplete across all arms.
[Main GFX comparison map](../docs/gfx-qualitative.md) ·
[Fine cab comparison map](../docs/gfx-green-mesh.md).

The fixed camera replay reproduces the mean parent and V120. Repeat
regains 0.02439 dB unseen over the mean parent and leads V120 unseen by
0.00473 dB. Its known-camera mean trails V120. All three new camera
points are in the source-bound chart. The canonical photo worker has
started, so the three full427 scores remain blank. [Camera replay](../docs/local-redraw-stability.md#fixed-camera-panels) ·
[PSNR history](../docs/performance-history.md).
