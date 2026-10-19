# Where the bank-context ADC detail regression occurs

The ADC-only weak period4 deficit is already present in the trained bank model's
RGB output **before its final directional correction**. Zeroing the bank logits
does not restore the detail. This locates the observed deficit within the
inference path; it does not establish which training gradients caused it.

[Complete results, all groups, paired contrasts and independent audit](results/directional-bank-component-diagnostic-v1.json).
This diagnoses the fixed checkpoints from the
[completed V80/V81 review](directional-bank-original4k-review.md); it creates no
new checkpoint, training updates, promotion or study extension. That review
retains the exact-GT native triplets and cached GFX3879/3880 qualitative crops.

## Fixed observations and interventions

The diagnostic repeats all448 original observations:24 carrier configurations
and four flat configurations, each with four CFAs and four noise draws.
Images are native256 with ROI `[48,48,160,160]`, seed20261016. Carrier levels
are.01/.18, relative contrasts.02/.1 and periods4/8/16 pixels. Conditions are
ADC-only (shot/read variance0/0) and ISO12800 prior (.00256/.0000262144), both
exposure1. These are declared noise priors, not measured camera calibrations.
WB `[2,1,1.5]` and camera transport match the original protocol. Gain is signed
cosine response after linear-sRGB transport; carrier frequency enters scoring
only. Each reported mean has16 CFA/draw cases, without scene or training-seed
confidence claims. No display transform is applied to these numerical metrics.

Five modes retain the original FP32/channels-last inference settings:

- `control/full` and `bank/full`: unchanged trained outputs.
- `control/base` and `bank/base`: the RGB tensor entering the final directional
  module, after the same trunk forward and inverse normalization.
- `bank/bank-logits-zero`: replay that final module with its bank executed
  normally, then replace only the bank's output logits with zeros.

The trunk's feature-return path stays intact. Every complete final-module replay
is bitwise identical to its corresponding full prediction. The bank intervention
keeps candidate ordering and module presence unchanged. Its effect is conditional
on the trained base and other logits; nonlinear mixing prevents interpreting it
as an independently trained additive component.

## The adverse ADC case

For level.01/contrast.02/period4, mean signed gain is:

| Mode | Signed gain |
| --- | ---: |
| Control full | 0.79645993 |
| Control base | 0.80325060 |
| Bank full | 0.46707526 |
| Bank base | 0.46710520 |
| Bank logits zero | 0.46639836 |

The base difference is−.33614540. The complete directional correction changes
gain by−.00679067 in the control and−.00002994 in the bank model, leaving the
full-model difference−.32938467. The conditional contribution of bank logits is
**+.00067690**; zeroing them slightly worsens this case. Linear-sRGB RMSE also
remains worse at the base:7.62140e-5 bank versus3.12935e-5 control.

All ADC-only variance inputs use the directional module's1e-8 floor, and no
inputs in this panel are censored. Crucially, the failing case has **zero bank
input clipping** in every CFA. Across the complete ADC panel, the mean clipped
fraction is.215665; the failing case cannot be attributed to direct clipping
at inference. These observations do not establish an optimization mechanism or
the effect of changing the floor during training.

## High-noise and other cases

| Level/contrast/period, ISO12800 prior | Control full | Bank base | Bank logits zero | Bank full | Conditional bank contribution |
| --- | ---: | ---: | ---: | ---: | ---: |
| .01/.1/8 | .00020846 | −.00213394 | −.00142398 | .00027911 | +.00170308 |
| .18/.02/16 | .29495479 | .29419274 | .29696984 | .29846162 | +.00149179 |

The dark case remains nearly suppressed. The full matched gains remain far
below the original+.05 requirements. The direct contribution also varies across
the complete panel: ADC-only level.18/contrast.1/period4 changes by−.02501514
when bank logits are enabled. High-noise flat spatial-luma RMS is
.00015102609/.00051232600 with the full bank versus
.00015010467/.00051647386 with its logits zero at levels.01/.18. A simple
global enable/disable decision therefore trades different errors.

A useful next training investigation is to isolate how bank conditioning sends
gradients into the common RGB network, with fixed data and an explicit gradient
audit before any new matched study. These fixed-weight results alone cannot
select a remedy or justify continuing the closed4k budgets.

## Verification and reproducibility

Both checkpoint files, complete model states and official DINO tensors retain
their hashes. V80 checkpoint SHA256 is
`6cd2295b945c38c95855dd6c7bb44380f12a6f48d56329d2103ec0793a66c2d9`;
V81 is `d05c1774a25164de0ce00b8210109c6d63930b14161f985c1c344bd4839eab42`.
All896 full-model rows replay the published metrics: maximum absolute gain
error5.13e-7 and other-metric error9.25e-9, below predeclared1e-4/1e-7 bounds.
The independent scalar audit checks2240 unique rows,140 groups and3760 summary
values (maximum arithmetic discrepancy2.23e-16), plus236 frozen source files.
It verifies saved scalars and file hashes; it does not independently regenerate
model tensors or per-case metrics.

The initial CUDA setup attempt failed before inference because its allocator
limit received an unindexed device. Its source, plan and failure remain bound
in the result. The corrected version passed a fresh64px CPU engineering
preflight before the complete256px CUDA diagnostic. No original photo was read.

The archived plan and work tree are under
`.cache/experiments/directional-bank-component-diagnostic-v2/`. Run the separate
read-only scalar audit with a fresh output path:

```bash
CUDA_VISIBLE_DEVICES='' .venv/bin/python3 -P scripts/audit_directional_bank_components.py \
  .cache/experiments/directional-bank-component-diagnostic-v2 \
  .cache/experiments/directional-bank-component-diagnostic-v2/repeated-audit.json
```
