# Find narrower exterior RAW peaks and preserve shorter restart intervals

Recorded: 2026-11-18T17:52:14-08:00 (America/Los_Angeles).

On 20 new held-out photographs with two redraws, exterior spectral
prominence raises weak-frequency hits from 3/40 to 15/40. At a shared
flat calibration budget, intact recovery rises from 24.27% to 38.89%
with more coherent leakage into gaps. Limiting both calibration
gap and flat RMS retains a 6.36-point recovery gain and lowers
intact increment error by 4.764 DN16. Held-out gap RMS is still
higher. The standing sky is pixel-identical. The left cab contains
unelected candidates near both earlier RAW peaks, while the right
lacks the required two-tile evidence. Both cab profiles, both ROIs,
the main sky, building, foliage and fence were viewed at native scale.
[Report and crop provenance](../docs/donor-peak-prominence.md).

The local arm's second RAM-floor stop discarded work beyond the
last verified 2,500 checkpoint. The recovery controller now invokes
the original worker in segments of at most 500 updates and combines
the validated traces at the original milestones. The plan, data order,
checkpoint format, optimizer, EMA and total learning-rate horizon
stay fixed. The local update-3,000 checkpoint verifies 1,000
byte-identical replay scenes, and the worker has started the
next segment from that checkpoint. [Run and matched review status](../docs/scene-full-epoch.md#execution-status).
