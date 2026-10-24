# Contrast-normalized band supervision diagnosis

Recorded: 2026-10-24T07:36:55-07:00 (America/Los_Angeles).

Previous goal turn was progress: cc70fee added and launched the independent
saved-prediction review queue. This turn revalidated all three exact live
owners: training 867877/1792848017.25, evaluation 868302/1792848232.8 and
independent audit 925140/1792851360.58. Both reviewers waited without children;
V114 was at step 4150 initially. The current objective remains open.

The completed six-versus-32 reviewed-ROI comparison already showed little photo
effect, so this turn investigated supervision rather than adding another ROI
bank. A new source-frozen CPU study reuses the 108 native 256 training-source
observations/predictions from the earlier V102 epsilon study: 12 selected sources,
contrasts 1/.25/.025 and ADC/ISO100/ISO12800. They are historical V102 outputs,
not V112 or pending V114/V115 results. There is no noise regeneration, corpus
rescan, RAW decode, learned/encoder call, optimizer update or CUDA activity.

Baseline uses the current recipe's epsilon .0003 and reproduces all 108 saved
gradient norms and correction slopes exactly. Two predeclared additions operate
on reflected 3x3 mean minus 9x9 mean camera RGB: an absolute band term weighted .1,
and a normalized term weighted .0003 with per-image clean-target band RMS floored
at .001 and dimensionless epsilon .1. Targets provide synthetic supervision only.
All 9x9 neighbors/channels must be valid, and an 8-pixel border is omitted. The
prototype remains separate from production losses, trainer and active recipes.

At contrast x.025, normalized-term median slope ratios are 1.1892/1.1744/1.1729,
with gradient-norm ratios 1.0411/1.0545/1.0327. Correction per gradient norm rises
1.1510/1.1143/1.1347 over ADC/ISO100/ISO12800, respectively. Eligibility is 11/12,
12/12,12/12; other gradient/cosine statistics retain all 12 cases. The selected
analysis direction shares the loss band, so the result is targeted. Separate
predeclared 1-5 directions show smaller 1.7/1.7/8.0% gains; 5-17 directions gain
9.7/7.2/6.8%. This does not solve the finest-detail problem or prove trained
quality. Absolute-band pressure has more effect at ordinary contrast.

Independent NumPy64 summed-area-table finite differences check all 216 new-term
directional derivatives, maximum absolute difference 6.13e-11. Eight focused
mathematical tests pass in 3.82s, covering values/derivatives, flat/invalid targets,
constant camera offsets, per-image batching and normalization. Ruff passes.
Actual execution forbids module forwards, preserves Torch RNG and keeps all 324
baseline/new-term gradient tensors. The recorded v1 completes successfully with
no scientific retry. Original machine receipts and executed sources are intact.

Published a standalone PNG/SVG figure with complete group/secondary-band data;
actually viewed the chart at original resolution. Ratios and descriptive IQRs
are labeled as output-gradient measurements, not confidence intervals or image
quality. The normalized term is a candidate for later matched training after
the current Tiny/Small comparison establishes the useful baseline. It has not
been integrated into production or scheduled as a new quality run.

Updated current research and loss/conditioning docs to reflect completed V112
results and the actual .0003 working recipe. Removed stale claims that the
loss-scale trial remained active or V104 was still the training baseline;
the original version-specific observations and receipts remain unchanged.

[Diagnosis and figure](../docs/contrast-normalized-band-supervision.md) ·
[Full execution/source/data receipt](../docs/results/band-supervision-output-gradients-v1.json).
Private frozen sources, arrays and publication driver:
`.cache/current-quality-20261023-v1/band-supervision-gradient-v1/`.

Final verification at 2026-10-24 07:41 PDT: all fifteen frozen plan guards
pass, public prototype/test hashes match the actual publication receipt, local
Markdown links resolve, and Ruff passes. V114 has logged step
5450; all three exact owners remain live and both reviewers have no children.
The selector still points to V112. No completed numerical experiment was rerun
for publication or bookkeeping. The loss additions differ in effective scale
and smoothing, so their comparison does not isolate normalization alone.

The generated Matplotlib SVG uses valid trailing spaces in path data. Extended
the existing scoped SVG attribute rule to this new figure directory, preserving
its original receipt-bound bytes. Final staged whitespace checks pass; PNG/SVG
hashes still match the figure receipt, and the standalone SVG parses as XML.
