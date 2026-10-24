# Review V112 eight-view quality on fixed material and real captures

Recorded: 2026-10-24T13:59:58-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress by implementing and queuing the
matched V114/V116 retained-output comparison. I verified all seven original
owners live at the start of this turn; V115 was at9,350/20,000. The existing
training/evaluation/audit chain remained unchanged throughout this work.

Ran the current V112 weights with the existing public eight-view policy on the
original twelve material/two adverse camera/six GFX observations and four
previously identified color cases787,1008,1035,1020. All192 actual model and
encoder views completed once on CPU2/IEEE FP32, with zero optimizer updates,
noise draws or RAW decodes. Each identity view contributes to the new ensemble;
no separate control-only inference was added. The run took844.32s on CPU; this
is not a GB10 full-frame timing result. All91 initial EMA tensors match V112;
weights, official frozen encoder, input values and Torch RNG stay unchanged.

All twelve material PSNRs improve versus V112 single, from+.06221 to+.61416dB.
ADC/ISO100/ISO12800 mean gains are+.54335/.27285/.07936dB; chroma/gradient means
also fall in every condition. Both dark M100 crops gain+.17599/+.23075dB but
remain below stronger RawNIND; Coulicoco is still slightly below V104 eight
views. All four selected color cases improve in mean bias and centered RMS over
V112 single. Case1035 changes50.89→42.79DN16, without establishing a new
full-grid maximum. No full427/camera/color-grid or102MP V112-eight-view result
is claimed.

The independent review reconstructs all24 means exactly and checks all numeric
methods with separate NumPy64/Torch64 arithmetic, maximum difference7.11e-15.
It reuses prior V104 eight-view and stronger RawNIND arrays. I viewed all140
native160 cells across six boards. Small bark changes accompany PSNR gains;
high-noise feathers/fur/canopy, real foliage and saturated signs remain soft.
The finer1/8–1/3 band shows little added projected signal. Both real-reference
paths remain explicitly approximate, never exact GT.

The first metadata setup used the wrong saved GFX role name and stopped before
model loading; its source snapshot and zero-forward failure remain. A fresh v2
completed inference. Two array-only analysis attempts exposed an extra AHD
metric and a separately stored GFX reference. Their sources/logs/partial images
remain intact. Corrected analysis consumes the same saved predictions; no neural
work was repeated to repair reporting.

Published the measured quality mode, unchanged native images and two small
noisy/restored/exact-GT triplets, updating README/current-model/eight-view/GFX
guides promptly. The trained baseline stays V112; original Tiny/Small and V116
data work continues. This useful mode does not solve broad real-photo superiority,
faint detail or100MP/10s.

[Performance report and native comparisons](../docs/v112-eight-view.md) ·
[Executed evidence](../docs/results/v112-dihedral8-pilot-v1.json).
