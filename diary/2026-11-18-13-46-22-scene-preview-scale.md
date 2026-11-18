# Test scene preview sampling and output bands

Recorded: 2026-11-18T13:46:22-08:00 (America/Los_Angeles).

Replayed both spatial EMAs on the fixed GFX crops at 1,024, 2,048
and 3,072 preview pixels plus a resampled 2,048 control. All sixteen
native boards retain smooth sky, coarse crossings and incomplete
fine cab crossings. The 3,072 input grid can sample the existing
mesh proposals without geometric aliasing. The learned output
shows little fine recovery.

The 64-photo exact-target ISO6400 replay finds 0.083–0.095 DN16
lower flat-core RMS with a denser preview. Resampling the coarse
guide yields a similar gain. Fine detail changes little. Separating
the aligned scene correction by output frequency brings fine scores
close to the masked guide on the fainter half, with the direction of
the error benefit changing across draws.

[Preview and band study](../docs/scene-preview-scale.md) ·
[Native main review](../docs/gfx-qualitative.md) ·
[Native cab review](../docs/gfx-green-mesh.md).
