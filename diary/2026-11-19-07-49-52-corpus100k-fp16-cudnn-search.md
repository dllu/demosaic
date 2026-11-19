# Full-frame FP16 cuDNN search

Recorded: 2026-11-19T07:49:52-08:00 (America/Los_Angeles).


Fresh cuDNN FP16 searches across four processes and eight complete
DSCF3879 restores do not confirm the earlier resident-batch speed gain.
Heuristic means are 39.13 s first and 34.26 s warm. Search means are
37.88 and 37.16 s. The shared GB10 has wide between-run timing
variation. Separate searches change the RGB16 result by 0.242 DN16 RMS.
Each tuned export differs from the heuristic output by 0.259 DN16 RMS.

I viewed all eight standing native boards, two exact-target comparisons
and both worst-code neighborhoods. Sky, foliage and fence structure
look the same under the matched views. The clipped cyclist retains the
same visible color error, with a measurable 26.28 DN16 crop difference.
The current supported path is ordinary CUDA FP16 with 512-pixel tiles,
64 pixels of overlap and batch four. Thirty-seven inference tests passed.
This study uses the existing EMA. Its broad panel coverage comes from
the earlier ordinary and TensorRT FP16 runs.
[New timing and crop report](../docs/corpus100k-cudnn-fp16.md) ·
[Main GFX review map](../docs/gfx-qualitative.md) ·
[Fine cab review map](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
