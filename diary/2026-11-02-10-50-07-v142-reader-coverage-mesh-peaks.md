# V142 actual reader coverage and fixed mesh-peak supplement

Recorded: 2026-11-02T10:50:07-08:00 (America/Los_Angeles).

The previous goal turn made concrete progress: commit9def8bc publishes the
completed V141 loss/native/flat review, and the V142 data-only production owner
continues without restart. Both original V142 controller and worker are live
at this turn's inspection; the original1k recipe/budget stays fixed.

A model-free CPU replay inspects all773 scheduled mesh reads from the exact
frozen reader, with matched empty counterfactuals through identical geometry.
There are397 present and376 absent sources across7,632 Commons/16,000 overall
target slots. Every absent target equals its empty counterpart exactly.
All12 logged crossed-line source recipes in the saved source-loss prefix match
exactly. The remaining scheduled reads do not prove that future updates have
already executed; terminal training remains required.

Present post-geometry median detail RMS/sampled level is.5261%, interquartile
.1851–1.3402%; exact empty area median61.589%, interquartile50.731–69.389%.
Generated level median.02637. Two present sources have pre-exposure peak detail
below half a16-bit code, but these are scene-linear source units before camera
transport and random exposure. They do not establish actual sensor visibility.
This describes modest structural training support, not a failure cause or
measured quality gain.

A separate supplement is fixed before V142 output collection: same two256px
windows, same all10 input-only noisy-green frequency selections from Oct25,
same nearby3879 conditioning. It will compare V120/V129/V141/V142 saved powers,
using predictions already required by the primary review. No new inference,
noise, RAW, window/profile selection or fitted threshold is introduced.
Independent weighted-plane least squares and explicit Fourier rows match
30 saved-control peak/method cases /540 complex coefficients, maximum power
difference3.02e−14. Candidate outputs remain pending. These ratios include
observed noise and cannot be called transfer gains, correct lattice recovery,
quality scores or flat-region safety.

[Reader receipt](../docs/results/v142-crossed-line-source-coverage-v1.json) ·
[Prospective mesh supplement and arithmetic preflight](../docs/results/v142-mesh-peaks-setup-v1.json).
Keep V120 recommended until actual numerical/native/flat evidence supports a
useful alternative; ISO100 independent captures remain qualitative references.
