# Close the isolated WGCAN RAW/Malvar transfer pilot

Pinned the official WGCAN source at
87413dd280af8228f34fe33188136077ad81ca68. Downloaded30 files with size and
Git-blob checks, including the released RAW checkpoint SHA256
61ca1440ade7e9230af46f4d90644e05255637048aac24152b0ab19fff24ed98.
The July2026 paper/implementation use wavelet-guided RAW restoration followed
by an ISP-trained RGB stage. Root/separate weight terms remain unverified;
source/weights stay isolated, outside production and git.

Original full-model engineering strictly matches294 tensors/11,681,731
parameters and passes all4 Bayer phases, repeat/input/state/RNG, independent
Haar checks and bitwise equality of early RAW readout to full-model RAW.
The initial helper's incorrect color_indices argument failed before inference;
its separate failure is preserved. The corrected check passes unchanged model
source. Published test script/API mismatch is handled by calling forward(x).

Froze six existing observations before predictions: two exact-GT photo256
contexts plus sky/building/foliage/fence GFX512 contexts. CPU/F32/B1/two threads,
CUDA hidden, original released input clipping and canonical CFA reflections;
unclipped RAW output feeds independent Malvar. No learned RGB ISP, fitting,
new noise draws, changed target or adaptation. Retained V43/V63 actual IEEE-CUDA
arrays are reused exactly. Plan3acb8946daf6e134b099ae2ba514c2ebcf06041c46f16c7ded1530ee68e2433e.
Worker377529/1792455004.62 and timeout377528 are genuinely absent after the
successful six-case terminal receipt.

Actually viewed both original-resolution boards/all30 cells before reading
numerical results. Canopy and building show candidate grids; fence wires
become a periodic mottled pattern. Candidate sRGB PSNR31.31272/24.50526 and
SSIM.892561/.734821 trail both retained controls on these two fixed crops.
This is a negative selected RAW-stage/Malvar composition result, not a ranking
of the full published model or an architectural diagnosis.

A rendering-loop metadata error copied candidate clamp/reflection/conditioning
labels onto12 retained receipts. Preserved original report and sidecars;
new review-v1 corrected-report/correction receipts alter metadata only, without
new inference, pixels or scores. Independent audit verifies all6 saved RAW
input/phase maps, all6 RGBs rebuilt bitwise from RAW, all54 native triplet panels,
all30 board cells/shared settings and12 FP64 PSNR replays within.000003005dB.
AuditSHA863447d9811120019a005a392d89b4571019087904c33bfc90d0b3510b63fcc3.
Published eight byte-identical PNGs, full metadata/result registry and report.

The original4k context experiment and new Commons producer remain separate;
their bound source/protocol/manifests are unchanged. No README promotion, new
data admission, full-suite or speed claim. Goal remains active.

[Report](../docs/wgcan-RAW-CPU-pilot.md).
