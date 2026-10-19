# Bank conditioning gradients and an opt-in training switch

The bank's candidate-minus-RGB descriptor sends measurable gradients into the
common network. On three original training batches at the fixed V81 EMA,
detaching only this descriptor changes the common parameter gradient by
**4.02%, 8.65% and 0.67%**, while predictions, losses and raw branch parameter
gradients remain bitwise identical. This makes the route independently
testable during training. It does not establish that detachment improves image
quality or caused the earlier ADC detail loss.

[Complete gradient records, frozen plan, source hashes and CPU engineering receipts](results/directional-bank-gradient-routing-v1.json).
The earlier [component diagnostic](directional-bank-component-diagnostic.md)
located that detail deficit before the final correction. The
[completed quality review](directional-bank-original4k-review.md) retains its
native exact-GT triplets and cached GFX3879/3880 comparisons. Its checkpoints,
budgets, decisions and working model remain unchanged.

## What was measured

The same trained V81-original4000 EMA is used for both backward passes. A
pre-hook detaches only the tensor entering the bank network in the second pass.
No optimizer is constructed for this diagnostic. Both passes require identical
prediction, auxiliary mosaic, loss terms, feature-cut gradient and all14 raw
directional/bank parameter gradients. All89 common trainable parameter tensors
change. The complete model state remains
`79d48ac40627bb5b86cb84d574d7d4d6fcddaba812e51067655ad7ac1e26d693`;
official frozen DINO remains
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
The checkpoint SHA and all238 frozen source/config files are bound in the result.

The CUDA run covers15 paired backward cases /96 observations. Training uses
the first original batch from each domain: steps1/2/6, B16/native256/BF16,
seed51 and the unchanged4000-horizon recipe. Both seven-field model-input
hashes and original full-reference batch hashes match the training receipts.
Only the selected domains load data. Commons uses4×→geometry/PSF→area2;
native128 and paired32 remain fixed. The prepared private150 extension is inactive.

| Training batch | Relative change in base-tensor gradient | Relative change in common parameter gradient |
| --- | ---: | ---: |
| Commons, step1 | 17.6018% | 4.0228% |
| Native RAW, step2 | 9.7202% | 8.6499% |
| Paired RAW, step6 | 0.6833% | 0.6662% |

Relative change means `||connected − detached||₂ / ||connected||₂`;
common gradients include the RGB network and trainable context projections.
Losses are the actual sensor-valid reconstruction objective or measured-CFA
paired objective. The comparison preserves their targets and masks.

The other12 cases are native256/FP32 carrier loss-Jacobian fixtures: three
signals, four CFAs and four noise draws each, seed20261016. They use the
original WB/camera/noise settings. These low-level gray signals do not clip,
so the sensor-valid clean target coincides with the original target. Target and
known frequency never enter the model forward. These are gradient measurements,
not new quality scores or confidence intervals.

| Level/contrast/period and condition | Common-gradient relative change across CFAs |
| --- | ---: |
| .01/.02/4, ADC-only | 0.0699–0.1247% |
| .01/.1/8, ISO12800 prior | 0.2140–0.4642% |
| .18/.02/16, ISO12800 prior | 0.0094–0.0722% |

The adverse ADC fixture therefore shows a small present-weight gradient
contribution through this route. It does not identify the cause of the much
larger historical signed-gain deficit, or bound accumulated optimization effects.
All15 CUDA gradient norms are below the clipping threshold1 in both passes;
clipped and raw gradients are identical here. This does not make clipping
irrelevant at other training steps.

## Optional behavior and verification

For a bank-enabled model, set:

```yaml
model:
  raw_directional_bank_detach_input: true
```

This stops gradients through the noise-normalized bank descriptor to the RGB
base, and to RAW inputs if they require gradients. It preserves the descriptor's
values, all bank parameters and their learning, the local directional path,
RGB/DINO feature path and final residual. It neither freezes the RGB network
nor removes every gradient from the correction into that network.

The option defaults false, requires bank context and adds no parameters or state
tensors. Old checkpoint configurations normalize to false. A changed setting is
rejected on resume; use fresh initialization for a separate comparison.

The39 focused tests pass, including FP32/BF16 equivalence to the diagnostic
hook, exact head/feature gradients, a changed base gradient, continued bank
learning, checkpoint roundtrip, legacy default and invalid combinations.
Another45 model/configuration/resume tests pass. A genuine V63/DINO CPU
preflight performs six B1/native64/FP32 updates and an independent3+3 restart
under the original4000-step schedule. Model/EMA/AdamW/RNG/best state and all
six training rows match, with105/105/103 finite state entries. Both bank head
tensors learn, and changed-policy resume fails before a training batch loads.
The12 optimizer updates are discarded engineering work; tiny logged validation
outputs are not used as model-quality evidence.

Two harness corrections are preserved. The first gradient attempt included
paired supervision arrays in a model-input-only hash; the corrected freeze
passed a fresh CPU preflight and all original CUDA identities. The CPU optimizer
runner completed training and restart checks but its final head-learning check
looked for parameters in PixelShuffle module4. A separate saved-checkpoint audit
checked the actual Conv2d module5 and completed the resume-policy check, without
retraining. The public receipt distinguishes those executions.

The actual CUDA optimizer check also completes six B16/native256/BF16 updates
per setting, with strict execution and the original4000-step horizon. Initial
model values, outputs, all103 raw gradients, all six input batches and final
RNG match between settings. Both retain105/105/103 finite model/EMA/AdamW state
entries, with frozen official DINO. The common model tensors then diverge as
the learned bank opens the gradient route. These12 additional CUDA updates are
discarded; their startup/validation-inclusive allocation peaks are recorded in
the receipt and are not throughput measurements.

A separately predeclared quality trial remains to be done. No production
training, default change, full-frame export, protected-final score or model
promotion follows these engineering results.
