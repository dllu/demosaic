# What smaller gradient smoothing changes on the actual mixed batch

The smaller epsilon strengthens the gradient-loss term, but its effect on the
complete output gradient is much smaller on the sampled dark noisy mesh.
This helps explain why a larger derivative alone need not teach visible detail;
it does not establish the cause of V143's trained results.

[Machine results](results/crossed-line-output-loss-gradients-v1.json) ·
[Executable diagnostic](../scripts/diagnose_crossed_line_loss_gradients.py) ·
[V143 training and quality](v143-crossed-gradient5000.md).

The diagnostic reuses the actual first V143 B16 inputs and saved initial
outputs, which match V142. It differentiates the complete reconstruction loss
with pixel epsilon 0.0003 and gradient epsilon 0.0003 versus 0.00003. Both
reductions retain the actual batch size, masks and auxiliary loss. No model,
optimizer, new noise or RAW decoding runs. CPU FP32 uses one thread.

There are ten photographic, two procedural, one smooth-field and three
crossed-line examples in this selected batch. All three meshes are present;
there is no absent-mesh example. The band is the fixed camera-RGB difference
between reflected 3×3 and 9×9 means, omitting the outer eight pixels.

| Actual mesh example | Missing target-band coefficient | Weighted gradient-term norm ratio | Complete RGB loss-gradient norm ratio | Corrective directional-derivative ratio |
| --- | ---: | ---: | ---: | ---: |
| Index 9, ADC only | −0.00531 | 2.940 | 1.170 | 0.787 |
| Index 12, dark noisy | 1.37394 | 3.389 | 1.083 | 1.076 |
| Index 15, ADC only | 0.00466 | 3.303 | 1.173 | 3.973 |

Ratios divide smaller-epsilon by baseline. The missing-band coefficient is
`<target − prediction, band> / <band, band>`; zero means no missing projection,
and a negative value indicates overprojection. The corrective direction is
that signed coefficient times the band. Both directional derivatives are
negative for these examples, so the ratio compares local descent slopes.
The ADC examples already have almost the correct band projection, which makes
their corrective ratios poor measures of a useful detail improvement.

The dark noisy example's target-band RMS is 2.995×10⁻⁶ in linear camera RGB,
with shot 1.54957×10⁻⁵ and read variance 3.24308×10⁻⁹. Reducing epsilon raises
its weighted gradient-term norm 3.389×, but the complete output-gradient norm
only 8.25% and the selected corrective slope 7.55%. Other loss terms still
dominate. These are output gradients, not network-parameter gradients or
optimizer contributions after clipping; none predicts learned quality alone.

Twelve complete-batch loss/term scalars match the actual V142/V143 first-step
GPU logs within rtol 2×10⁻⁵ and atol 2×10⁻⁷. An independent NumPy64 divergence,
sRGB derivative and color-matrix VJP checks 6,291,456 RGB gradient values
against autograd using the actual FP32 forward intermediates. Maximum absolute
error is below 1.84×10⁻¹² and relative L2 error below 1.78×10⁻⁷. Auxiliary
gradients match exactly; the change in the total RGB gradient equals the change
in the gradient term within 4.55×10⁻¹². Python, NumPy and Torch RNG states are
unchanged. A formatting-corrected replay gives identical numeric results;
both executions and the original operator bytes remain cached.

This motivates measuring the balance of complete losses and the prevalence
of noisy weak examples before increasing a coefficient. It does not justify
a larger weight without matched training and absent-detail/flat checks.
