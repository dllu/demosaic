# Contrast-normalized band supervision diagnosis

**A target-normalized band term directs more of the output gradient toward
missing faint structure in these saved training examples.** At additional
contrast ×.025, its median corrective slope rises 17–19% while total gradient
norm rises 3–5%, relative to epsilon .0003. This is a loss diagnosis, with no
new trained model or restored-quality claim. V112 remains the current baseline;
the V114/V115 comparison continues unchanged.

![Corrective slope per gradient magnitude on saved V102 predictions](images/band-supervision-gradients/band-gradient-response.png)

[Standalone SVG](images/band-supervision-gradients/band-gradient-response.svg) ·
[Figure data/definitions](images/band-supervision-gradients/figure.json) ·
[Execution, all groups and secondary bands](results/band-supervision-output-gradients-v1.json) ·
[Prototype](../scripts/probe_band_supervision.py).
Points are medians with interquartile ranges over eligible selected training
sources, not confidence intervals. Eligibility counts are shown.

## Inputs and objective

The 108 native256 inputs, targets and predictions come from the
[earlier epsilon diagnosis](loss-smoothing-detail.md): 12 selected **training**
sources, additional contrast ×1/.25/.025, ADC-only/ISO100/ISO12800 and RGGB.
These are historical **V102** restorations, not new V112 predictions. Six sources
are reviewed photographic ROIs and six are newly eligible corpus photographs.
No validation/test/GFX targets enter this study.

The baseline uses the **current recipe's epsilon .0003**, retaining its original
linear/rendered/gradient/highlight/sensor coefficients. All 108 baseline gradient
norms and correction slopes reproduce saved values exactly. The two additions
are fixed before execution; combined gradients are baseline plus the new term's
gradient. All 324 output-gradient tensors are retained, with no network Jacobian
or optimizer update evaluated.
The auxiliary CFA term samples the restored output, matching the earlier
diagnostic; this is not the network's full parameter gradient.

Let `B` be reflected 3×3 mean minus 9×9 mean, and `e = B(prediction − target)`.
Only exact synthetic targets are considered. A 9×9 neighborhood must have all
camera RGB channels within [0,.98), and the outer eight pixels are omitted.

| Term | Additional penalty averaged over valid pixels/images |
| --- | --- |
| Absolute band | `.1 × (sqrt(e² + .0003²) − .0003)` |
| Target-normalized band | `.0003 × (sqrt((e/s)² + .1²) − .1)` |

Here `s` is each image's valid clean-target band RMS, floored at **.001** and
detached from backpropagation. Empty valid regions contribute zero. Targets
supply training supervision only; no target-dependent inference correction
is proposed. The prototype is not connected to production training.
The additions differ in effective weight and smoothing as well as normalization;
this comparison does not isolate normalization alone.

The analysis direction projects target-minus-prediction onto the exact target's
3–9 band. A negative derivative means that correcting this component lowers
the objective. Slope ratios require a positive missing coefficient and negative
baseline slope; gradient-norm and cosine summaries retain all 12 cases per group.

## Faint-contrast result

Median ratios for the normalized addition versus baseline at ×.025:

| Observation | Gradient norm | Corrective slope | Correction per gradient norm | Eligible |
| --- | ---: | ---: | ---: | ---: |
| ADC-only | 1.0411× | 1.1892× | 1.1510× | 11/12 |
| ISO100 | 1.0545× | 1.1744× | 1.1143× | 12/12 |
| ISO12800 | 1.0327× | 1.1729× | 1.1347× | 12/12 |

The absolute-band addition improves correction per gradient norm by only 3–4%
in these faint groups. At ordinary contrast it has more effect than the
normalized term. Normalization allocates extra pressure preferentially to faint
targets; this is not a uniform improvement across every type of detail.

The main direction shares the proposed loss's band, so improvement there is
expected. Separate, predeclared 1–5 and 5–17 mean-difference directions check
other scales. At ×.025, normalized correction per gradient norm rises only
**1.7/1.7/8.0%** in the finer 1–5 band for ADC/ISO100/ISO12800, and 9.7/7.2/6.8%
in the coarser 5–17 band. The finest-detail problem remains open. These
projections use the same selected sources, not independent generalization data.

Independent NumPy64 summed-area-table arithmetic checks all 216 new-term
directional derivatives; maximum absolute discrepancy is **6.2e-11**. Eight
tests cover independent values/derivatives, flat and invalid targets, camera
mean invariance, per-image batching and contrast normalization. The actual
study forbids module forwards, initializes no CUDA and preserves Torch RNG.
It performs zero new model/encoder calls, noise draws, RAW decodes or training
updates. Original sources and all completed receipts remain intact.

## Next quality question

The normalized term is a candidate for a later matched training comparison after
the current Tiny/Small results establish the useful architectural baseline.
This diagnosis does not show how network gradients, generalization, flat-field
artifacts, color tails or real foliage would change. Any trained comparison
still needs complete matched panels, native noisy / restored / GT triplets and
standing GFX foliage/fence and other regions. Paired/noisy references are outside
this prototype's exact-target supervision.
