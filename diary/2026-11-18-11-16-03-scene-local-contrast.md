# Qualify localized contrast in whole-scene training

Recorded: 2026-11-18T11:16:03-08:00 (America/Los_Angeles).

The training reader now supports a deterministic localized
contrast option. The source schedule, crop boxes and camera
recipe stay matched. Clean pixels outside the taper stay exact,
and every crop shares the RAW supplied to its scene preview.
The 48-source train-only preflight finds 45 qualifying crops.
Their mean lower/fine RMS retention is 79.8%/38.6%, while
a whole-crop transform at the original random scale keeps 26.2%
in both bands.

Centering the average corrects a small FP32 roundoff on constant
colors. The final filter is exact on constants and remains within
0.06 full-scale ADC code of its FP64 evaluation on the retained
actual targets. The prototype and stricter failed arithmetic
prechecks are preserved with the final receipts.

The actual trainer runs two discarded updates each in local-only
and spatial modes on identical modified observations. Adapter
gradients, frozen DINO identity and checkpoint reload pass.
No production continuation was started for this data option.
[Implementation, preflight and viewed training targets](../docs/scene-local-contrast-training.md).
