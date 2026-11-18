# Near-ADC residuals and noise-conditioning gap

Recorded: 2026-11-18T01:55:50-08:00 (America/Los_Angeles).


A sensor-weighted Malvar residual gains fine detail on the smallest
positive-noise prior. The first four held-out sources move from
3.653 to 2.486 DN16 weakest-band RMS with raw versus corrected 86k.
The correction raises fine-band error at the three higher noise
priors. At the intermediate prior, sRGB PSNR still improves.

Bright-yellow flat controls expose a much larger low-noise error
than the ADC zero-noise spot checks. With identical noisy RGGB
tensors, changing only conditioning from tiny positive to zero
moves the 86k worst channel bias from 7,428.72 to 10.58 DN16. The
same separation is reproduced on the ADC encoding and on GBRG
with residual Bayer-dependent error. A separate measured-residual
excess rule reduces the worst bias to 87.67 DN16 on the controls
that motivated it. All 1,376,000 executed slots through 86k
include 103,205 ADC-only slots and no positive prior at or below
eight full-signal ADC codes RMS. The lowest positive prior in
the ledger is 155.95 codes.

Both GFX families were reviewed for the positive-noise corrections.
The smooth sky and coarse crossings remain, with a small grain
change and no new fine cab crossings. The 16-photo panel, the
12-source guarded comparison and the paired zero-conditioning
replay are still collecting. Those twelve exclude the four
sources opened before selecting the eight-code guard.

The prior bark and fur comparison metadata printed an incorrect
crop rectangle. Every displayed pixel was independently reproduced
from the intended native coordinates. Renderer metadata now uses
the actual ROI argument, and an addendum preserves the original
receipt and images. The first calibration attempt called
`np.row_stack`, which this NumPy version has removed. The corrected
calculation uses `np.vstack`. Both sources and logs are archived.
The focused suite passed 47 tests.

[Near-ADC preflight](../docs/noisy-cfa-residual.md) ·
[Actual training conditions](../docs/results/noisy-cfa-residual-preflight-v1/training-noise-audit.json) ·
[Prior native ROI addendum](../docs/results/full-corpus-long86k-adc-panels-v1/native-roi-correction.json) ·
[Main GFX plates](../docs/gfx-qualitative.md) ·
[Cab GFX plates](../docs/gfx-green-mesh.md) ·
[Comparable PSNR history](../docs/performance-history.md).
