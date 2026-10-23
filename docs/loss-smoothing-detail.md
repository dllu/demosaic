# Loss smoothing and faint detail

**Smaller Charbonnier epsilon strengthens supervision of faint low-noise
detail, while increasing the overall output gradient more.** This fixed-V102
diagnostic motivates a later matched training test. The current loss and
Tiny/Small recipes remain unchanged; no restored-quality gain is established.

The production penalty is `sqrt(error² + 1e-6)`, so epsilon is **0.001**.
Its elementwise derivative is `error / sqrt(error² + epsilon²)`. Errors below
epsilon still contribute; their gradients are weaker than the limiting L1
gradient. Linear-camera and rendered losses each use their own numeric units.

![Charbonnier derivative and actual output-gradient responses at three contrast levels](images/charbonnier-loss-gradients/charbonnier-output-gradients.png)

[Standalone SVG](images/charbonnier-loss-gradients/charbonnier-output-gradients.svg) ·
[Figure data and definitions](images/charbonnier-loss-gradients/figure.json) ·
[All grouped results, execution receipts and hashes](results/charbonnier-detail-output-gradients-v1.json).
Bars show descriptive interquartile ranges, not confidence intervals.

## Actual inputs and measured gradients

The twelve sources are the previously fixed clean-reader checks for the
90,864-source corpus: six newly eligible photographs and all six original
reviewed fine-detail ROIs. Targets use the actual native256 training reader,
including its geometry, binning and any already-selected contrast attenuation.
Additional mean-preserving contrast factors **1, .25 and .025** operate on the
same targets without changing their mean, exposure or geometry.

Each has ADC-only, ISO100-prior and ISO12800-prior observations: **108 actual
CPU FP32 restorations**, with V102 final20k EMA, fixed RGGB/WB/matrix, exposure1
and declared physical shot/read conditioning. Every prediction then receives
the same three output-loss checks: epsilon **.001/.0003/.0001**. Only the
Charbonnier kernels change; loss coefficients, validity masks and the separate
absolute highlight penalty remain fixed. There is no optimizer update.

The default loss terms and output gradients reproduce the actual production
implementation exactly on all 108 cases. Independent NumPy F64 central
differences verify all 324 directional gradients, maximum absolute difference
**below 1.9e-10**. Saved input/prediction hashes are rechecked independently; weights,
frozen encoder, model configuration, parameter identities and Torch RNG stay
unchanged. The diagnostic initializes no CUDA.

The exact-target analysis band is the reflected 3×3 mean minus 9×9 mean in camera
RGB, with the outer 8 pixels omitted. Projecting target-minus-prediction onto
that band defines a corrective direction. A negative loss derivative means
that correction lowers the objective. The slope ratios below include positive
missing-band coefficients and negative default/alternative slopes; the displayed
counts expose excluded cases. All total-gradient statistics retain 12 sources.
The target band is available only for analysis.

## What smaller epsilon changes

Median ratios for **epsilon .0001 versus .001**:

| Additional contrast | Condition | Total gradient L2 | Missing-detail correction slope | Eligible cases |
| --- | --- | ---: | ---: | ---: |
| 1 | ADC-only | 1.117× | .947× | 7/12 |
| 1 | ISO100 | 1.117× | 1.057× | 10/12 |
| 1 | ISO12800 | 1.051× | 1.012× | 11/12 |
| .25 | ADC-only | 1.618× | 1.281× | 7/12 |
| .25 | ISO100 | 1.373× | 1.198× | 11/12 |
| .25 | ISO12800 | 1.150× | 1.039× | 12/12 |
| .025 | ADC-only | 2.522× | 2.180× | 11/12 |
| .025 | ISO100 | 2.034× | 1.585× | 12/12 |
| .025 | ISO12800 | 1.344× | 1.110× | 12/12 |

The .025 follow-up was chosen after the original 72-case analysis to include
signals near/below epsilon. Nine of the twelve source contexts have target-band
RMS at most .001; the median is **.000678**. This extra contrast reduction is
stronger than the current augmentation's .125–.5 range. It is a stress case,
with the original 72 results preserved.

At that faint contrast, the median fraction of camera-channel residuals below
.001 is 98.4% ADC-only, 92.7% ISO100 and 52.6% ISO12800. Smaller epsilon therefore
changes substantial low-noise supervision. The milder .0003 alternative raises
the ADC-only correction slope 1.760× and total gradient 1.831× in this group.
At high noise, the correction-slope increase is smaller than the total-gradient
increase. Median alignment of the negative gradient with the target-band
correction decreases in every group. Stronger gradients do not isolate useful
detail or prove a better training outcome.

These are selected training sources, one noise draw per case and a fixed
camera transform. They do not measure held-out quality, broad-camera/paired
loss behavior, gradients through the network or generalization after training.
The chosen band also does not cover every fine structure. A later matched
training comparison can test the idea while holding architecture, data,
initializer and budget fixed. The [current cleaned-data capacity comparison](convnext-small-capacity.md#prepared-matched-quality-trial)
keeps the original loss so its encoder comparison remains interpretable.
