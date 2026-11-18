# Bind the Corpus 20k broad benchmark

Recorded: 2026-11-18T04:42:02-08:00 (America/Los_Angeles).

The matched CPU collector closed all 3,162 canonical cases for V120 and
the Corpus 20k EMA. The fixed 427-photo sRGB PSNR is 37.09079 versus
37.04008 dB, a gain of 0.05071 dB. Corpus 20k improves 420 source means
and all seven condition means. Known/unseen measured-CFA changes are
+0.03285/−0.04067 dB. The latter match the prior camera-only publication
exactly. I checked all case, canonical-input and checkpoint bindings
and recombined the sealed per-observation metrics.

I regenerated the chart and inspected how the 20k and 100k points are
shown. The 100k full427 collection is still running. The separate NumPy
pixel rescore and full427 weak-band analysis are processing saved 20k
arrays. The existing native material and both GFX boards remain the
actual viewed evidence for this EMA. Fine crossings remain incomplete,
and the targeted ADC color cost is substantial.

[Completed broad report](../docs/full-corpus-control20k-primary.md) ·
[Updated PSNR history](../docs/performance-history.md) ·
[Main standing review](../docs/gfx-qualitative.md) ·
[Cab mesh review](../docs/gfx-green-mesh.md).
