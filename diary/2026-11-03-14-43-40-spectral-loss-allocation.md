# Spectral supervision allocation at zero initialization

Recorded: 2026-11-03T14:43:40-08:00 (America/Los_Angeles).

The preceding goal turn completed and published V149's six fixed endpoints and
66 native comparisons. That was progress: known CFA alignment and nine coherence
features did not recover useful new weak texture, so this turn tests supervision
allocation before expanding the head again. The broader objective remains
active and unmet.

The first frozen diagnostic takes the first 20 original batches per domain,
100 batches/400 cached observations. It evaluates the exact zero-head path with
constant support .5 and the current RGB/spectral objective, alongside post-output
and clean-peak-weighted spectral alternatives. No training update, new noise,
parent or DINO evaluation occurs. Ten full fresh-head forwards verify exact
initial output, loss and the shared real matrix-bias derivative. Peak allocated
CUDA is 5.84 GiB. The result shows ADC-only coefficient-gradient dominance;
peak boosting amplifies it rather than reallocating pressure toward noisy mesh.

The second frozen run repeats the same cohort and projects coefficient
cotangents through the actual initial frequency features into all 1,040 output
parameters. All other initial parameter gradients are zero. Ten complete-head
forwards check all 12 parameter tensors under both 2/16 DN floors, with maximum
relative vector difference 3.08e-6. The 100 additional hidden convolutions are
explicitly counted. Peak allocated CUDA is 7.36 GiB. Both workers completed
successfully and exited; original frozen sources/receipts remain unchanged.

The 15 ADC-only batches provide 99.9961% of summed squared initial parameter
gradient norms; 85 noisy batches provide the remainder. Post-output supervision
alone still gives ADC 99.9790%, and bounded peak weighting gives 99.9985%.
Changing only the training RGB/spectral floor from 2 to 16 DN lowers the share
to 88.3068%. Eighty-four noisy-batch gradients remain bit-exact; the remaining
noisy vector changes by relative L2 1.62e-5. Flat/photo ADC examples account for
the largest norm changes. Slopes and real photographic content make them
different from the constant ADC validation fields that stay exactly at parent.

An independent audit recomputes all projected vector norms in NumPy FP64,
checks 36,500 scalars, 78 Decimal reductions, vector linearity and every original
coefficient scalar (all exact). Public evidence preserves ten byte-exact copies,
the gradient arrays and both source versions, with 85 identical neural sources.

Separately audited all 1,000 completed V149 trace/noise bindings for all three
heads. Native control has 118 ADC batches and 882 noisy batches. Median logged
preclip norms are .298018/.017676; 35 ADC norms exceed 1, versus zero noisy.
ADC accounts for 97.311% of a cap-at-1 squared-norm proxy. This is magnitude
evidence, not measured parameter displacement or a causal proof about Adam.

Next compare identical fresh native matrix heads on all 4,000 adopted training
observations with matched 1k schedule, changing both RGB standard-deviation and
spectral variance floors together from 2 to 16 DN. Retain actual noisy blank and
quiet-region errors, every final raw/EMA endpoint and both standing real scenes,
priors/windows/JPEGs. Add held-out ADC photographic/sloped controls before
claiming a useful quality replacement. Neither a raised floor nor its gradient
allocation establishes better image quality yet. No inference default changes.

[Current diagnostic report](../docs/spectral-loss-allocation.md) ·
[Two-run evidence](../docs/results/spectral-loss-allocation-v1.json) ·
[Full training trace audit](../docs/results/spectral-loss-training-trace-v1.json).

