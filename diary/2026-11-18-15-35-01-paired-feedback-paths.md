# Isolate the noise coupling in the paired head

Recorded: 2026-11-18T15:35:01-08:00 (America/Los_Angeles).

Completed an inference replay of the frozen paired head using
96 ISO6400 photos, two independent query-donor pairings per
source and separate calibration and transfer photos. The parent
luminance guide from another exposure barely changes variance.
Using the other exposure's parent mosaic only in the innovation
adds 226 DN16² at matched response. Moving the complete guarded
correction to the extra capture brings its covariance term near
zero and lowers increment RMS 0.252 DN16 against Corpus 100k.

The single-frame innovation smoother lowers error 0.016 DN16
against a response-matched canonical head. Directional smoothing
recovers somewhat more response at the same flat budget, with
uncertain changes in increment error. Viewed all eight standing
boards and three native synthetic triplets. The sky stays smooth
and fine cab crossings remain incomplete. This study uses
frozen weights.
[Full report](../docs/paired-feedback-paths.md) ·
[Main GFX review](../docs/gfx-qualitative.md) ·
[Cab mesh review](../docs/gfx-green-mesh.md).
