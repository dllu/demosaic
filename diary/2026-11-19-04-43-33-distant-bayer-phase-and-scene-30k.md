# Gate Bayer phase and review matched scene 30k

Recorded: 2026-11-19T04:43:33-08:00 (America/Los_Angeles).

The distant phase gate uses four disjoint Bayer donors 64 pixels from
the query. The three matched arms from the frozen eight-donor parent
complete 672 updates each. Compared with fixed exterior phase, the
new route reduces natural flat RMS by 0.749 DN16 at ISO6400 and gains
another 0.362 planted-wire response points. It still adds 0.145 DN16
flat RMS and loses 0.061 points of fine response relative to ring8.
The missing-family gap-band audit finds slight leakage. Shifting the
distant measurements weakens the result. Rotating the directional
weights has little effect.
[Gate report, checkpoint and native evidence](../docs/bayer-distant-phase-gate.md).

I inspected three exact boards and both standing GFX families for the
new gate. The sky stays smooth and none of the small cab junctions
clearly reappears. The component is reported on its scoped panels,
with no comparable new broad PSNR scores. The focused suite passed
66 tests.
[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Performance history](../docs/performance-history.md).

The matched 30k pair completes all 256 exact-photo cases and the
four exact native comparisons. The local arm gains 0.121 independent
ISO6400 fine-response points over 25k with 0.037 DN16 higher flat RMS.
Changing the distant preview barely moves the spatial arm. Both
training traces cover 60,000 distinct photos. The local-only trace
has reached 65,000 distinct photos at update 32,500.
[Matched 30k review](../docs/scene-full-epoch-30k.md) ·
[32.5k local audit](../docs/results/scene-full-epoch-v1/local-032500-prefix.json).

The completed 30k standing review includes both cab ROIs, both
noise priors and the independent reference captures. The 25k and
30k direct boards show similar native detail. Broad panels remain
queued for the full 50k endpoints.
[Native standing review](../docs/scene-full-epoch-30k.md#standing-gfx100s-comparisons).
