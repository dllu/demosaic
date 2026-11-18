# Transport measured donor geometry and test the 50k ADC repair

Recorded: 2026-11-17T17:50:19-08:00 (America/Los_Angeles).

Measured quadratic donor geometry raises lower-noise far curved
response from 2.60% to 4.29% against fixed planar frequencies at
matched quiet RMS. The all-source response is essentially unchanged.
The richer initialization accepts six direction/profile combinations,
including one straight false curvature. Both versions fall back on
all eight real GFX regions. I viewed the native boards, including
both accepted ISO400 far examples. [Donor geometry review](../docs/donor-phase-geometry.md).

The calibrated ADC repair lowers the 50k channel-mean bias from
1,490 to 11.16 DN16 on the retained spot controls. It improves
faint sRGB and fine-band RMS relative to raw 50k. The corrected
50k band error remains higher than corrected V120. The GFX inputs
bypass the correction exactly. [50k ADC follow-up](../docs/full-corpus-long50k-native.md#calibrated-adc-follow-up).

[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md) ·
[Standard PSNR history](../docs/performance-history.md).
