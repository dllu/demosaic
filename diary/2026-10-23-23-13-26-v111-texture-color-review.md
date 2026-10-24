# V111 complete texture and color review

Recorded: 2026-10-23T23:13:26-07:00 (America/Los_Angeles).

V111 completed all 448 original weak-carrier/neutral-flat and 1,176 flat-color
observations on CPU2/IEEE FP32. The exact original worker and audit owner exited
successfully. No optimizer, CUDA, RAW decode or additional reference inference
was used beyond the four declared V104 parent replays.

NumPy64 independently rebuilds all color metrics exactly and all 896 weak/Malvar
rows within 1.58e-13, reproducing every original input and all 448 original
Malvar rows exactly. All 40 native cells were actually viewed: 15 texture,
20 original colors and five new post hoc worst-ADC cells. Original source/ROI,
conditioning, WB/matrix and display exposure are shared; all crops remain native
160 pixels.

At level .18 / relative contrast .02 / ISO12800, in-phase gain rises .05945 to
.08697 for period8 and .60487 to .62498 for period16. The finer pattern remains
mostly absent; its noncarrier RMS rises .000720 to .000813. Period16 residual
RMS falls slightly. Native V104/V111 carriers look close; this is not a broad
repair of fine texture.

High-noise color mean/p95/max channel-mean bias improves from19.34/59.85/115.84
to17.85/50.84/91.89 DN16. ADC-only bias worsens from14.46/43.70/1218.06
to27.64/45.43/2142.98 DN16. V111's new worst ADC field is bright neutral gray
(linear-sRGB .9), GBRG, case787, with green mean error +.0326997549 camera units.
All three models are shown at that identical field; the post hoc selection is
explicit. V111 has a slight green tint in RGB8 and a large float bias relative
to 16-bit precision. The original prospective cases and original V104 worst
field remain included. V102 retains the lower ADC flat-color bias.

The earlier combined V111 material/GFX and complete-camera reports remain
valid. Full427/V112 matched scores and full exports remain pending. Current
README/guides will show these strengths and weaknesses directly. Machine
receipts, prior artifacts and all twelve frozen plans retain their bytes.

[Complete execution, source hashes, numeric audit and native evidence](../docs/results/v111-texture-color-complete-v1.json).
