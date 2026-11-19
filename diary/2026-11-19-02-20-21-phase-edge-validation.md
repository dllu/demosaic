# Validate weak Bayer waveforms against a local edge

Recorded: 2026-11-19T02:20:21-08:00 (America/Los_Angeles).

Replayed the frozen local 20k phase head with center green pixels
split into discovery and validation folds. Exterior phase and
frequency are fixed before either fold is scored. The local step
competitor reduces false waveform addition in an exact zero-wire
gap from 15.45 to 11.76 DN16 at the same gain as the affine
comparison. On the 24 held-out ISO6400 wire backgrounds, the
photo-calibrated step gains 0.27 response points and lowers
absolute gap error by 0.49 DN16 against affine. Natural-photo
response still favors the local power gate at similar flat RMS.

Viewed three exact-target boards and eight standing GFX boards.
The sky stays smooth. Photo-calibrated edge evidence retains some
right-cab diagonals that local power suppresses under nominal
conditioning. Both ISO100 and JPEG references show fine junctions
that remain incomplete in the restores.
[Report and exact triplets](../docs/phase-edge-validation.md) ·
[Main scene map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).

Calibration, numerical review and native viewing are complete.
The crop policy uses the frozen parent and correction EMA.
Comparable broad PSNR remains tracked separately.
[PSNR history](../docs/performance-history.md).

Larger-corpus local-only training verifies 25,000 updates on
50,000 photos. Matched training verifies 23,500 updates on
47,000 photos per arm. Matched interim quality remains at 20k
while the spatial 25k checkpoint runs.
[Training coverage](../docs/scene-full-epoch.md#execution-status) ·
[Most recent matched quality](../docs/scene-full-epoch-20k.md).
