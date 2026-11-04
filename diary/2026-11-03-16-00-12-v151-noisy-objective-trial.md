# V151 noisy-only and peak-weighted objectives

Recorded: 2026-11-03T16:00:12-08:00 (America/Los_Angeles).

Previous goal turn was progress: V150 completed all four endpoints/72 native
figures and documented small actual noisy-flat and ADC photo gains, while the
high-ISO cab mesh remained missing. Its 16 DN objective becomes this trial's
control. The full trace still gives ADC 95.162% of a capped squared-norm proxy;
that is not Adam influence or a causal proof, but motivates a sharper test of
ADC supervision before another broad estimator change.

Three identical fresh 31,409-parameter native matrix heads replay the same 1,000
cached V148 batches/4,000 observations and V143 parents. All 12 initial tensors
match, and all 85 neural/inference files remain unchanged. 16 DN control,
noisy-only with ADC loss 0, and noisy-only with clean-spectrum weighting
`1+7*r/(1+r)` on coefficient MSE, where r uses clean four-phase power and the
floored frame-noise proxy. Weights 1..8 are not renormalized and do not reduce
the constant-target penalty within supervised noisy batches. All metadata and
targets enter loss only, never forward. Noisy peak weighting is not calibrated
probability or a flat-safety guarantee.

There are 118 ADC-only and 882 noisy batches. Candidates retain 1,000 full forward,
AdamW and EMA updates, with exactly zero ADC gradients. Existing optimizer
moments/weight decay still coast on those steps; the source/learning-rate clock
is unchanged. Thus 882 supervised batches/3,528 observations for both candidates
are explicitly distinguished from1,000 optimizer updates. Peak weighting runs
on 882 noisy batches. All physical inputs, source distribution/domain weights,
geometry, initialization, seed/horizon/schedule/clipping/EMA otherwise match.

All 13 new tests pass in 1.39 s: independent NumPy complex values/gradients across
four CFAs/ADC/high-noise cases, exact legacy 16 DN equivalence, exact baseline
weights/loss on constant targets and Adam motion with zero gradients. Current,
frozen and archived V150 16 DN outputs agree exactly on 28 cases (56 actual
forward-function evaluations) across 256/384/512/768 and all CFAs/real controls.
Three fresh CUDA 10 checks include genuine 8+2 restoration, all12 nonzero finite
parameter gradients over the prefix and explicit zero gradients on every
masked ADC step. Seven supervised/three coasting updates per candidate and
seven peak-weight evaluations. Peak allocated CUDA 4.08 GiB. Production restarts
fresh; no running worker is replaced or restarted.

All 6 final raw/EMA 1k endpoints cover the same822 cases (4,932 head calls) and
84 native figures (48 old fixed ROI/display boards + 36 repeated-cell triplets).
ADC photos/slopes are still executed/scored without an inference bypass. All
noisy/blank/quiet controls and both standing GFX scenes, priors, windows, JPEGs stay
in review; independent ISO100/AHD/JPEG references remain qualitative, not exact GT.
All validation/protected source IDs/captures/siblings remain outside training.
Only cached arrays are read, with zero new parent/DINO/noise calls and no
original/RAW/dataz access. This is adaptive reused validation, not independent
fresh evidence. All final endpoints stay fixed regardless of training loss.

The reporting preflight passes 64 parent cases / 280 scalars (maximum 1.24e-13),
with CUDA uninitialized and no new neural/noise calls. Checkpoint 250 contains 36
finite Adam states and finite raw/EMA tensors. Control raw/EMA/Adam matches
V150 floor16 exactly. Preparation records an active 324-row exact control trace
prefix and 39 ADC zero-loss/zero-norm rows per candidate, with both controllers
and the training worker verified live by PID/create time. Ten receipt copies
preserve their original bytes. Quality and actual native viewing remain pending;
the broad fine-detail/clean-sky objective remains active and unmet.

[Protocol/current status](../docs/noisy-objective-training.md) ·
[Preparation evidence](../docs/results/v151-noisy-objective-preparation-v1.json).


## Completed review — 2026-11-03T16:32:37-08:00 (America/Los_Angeles)

All three heads finish 1,000 updates; all 36 Adam states are finite. Control
trace, raw/EMA/Adam and all 1,644 final control prediction arrays reproduce
V150 floor16 exactly. All 118 candidate ADC steps have zero total loss and
gradient norm, while optimizer/EMA clocks continue; 882 supervised batches
per candidate. No noisy-only steps clip; one noisy peak step clips.

Noisy-only raw/EMA raises present-mesh response 7.22%/3.76% versus V143 and
lowers present-scene RMS .233%/.189%. Raw actual blank RMS rises .019%; EMA
lowers it .027%. Absolute response is still only .02361/.02285 of exact GT.
Native512 ISO6400 flat full RMS falls .100%/.146%, ISO12800 .111%/.163%.
Coarse changes are tiny/mixed. Quiet RMS beside strong patterns still rises
.154–.385%. Raw noisy-photo full RMS improves .0015–.0119%, but organic-band
errors and all four group responses remain worse than V143; EMA is mixed.

Peak8 mesh support collapses to about 2.06e-6/1.61e-6, leaving noisy output
almost at V143. Noisy-only support rises to .440/.424 while pre-support
proposal RMS falls, with nearly identical present/absent means: this does not
establish spatial selectivity. The target-weighted spectral loss does not
deliver useful noisy-detail recovery at this fixed horizon.

ADC photo RMS gain shrinks to .216–.227% for NoADC, .634–.658% for Peak8,
versus the control's 3.057–3.058%. NoADC reduces the control's roughly 28%
sloped-field coarse regression to .19–.29%; Peak8 remains 1.43–1.57% worse
than V143. All 48 constant ADC cases stay exactly at parent for all six
endpoints (288 exact predictions), which does not guarantee sloped-field safety.

All 822 cases / 4,932 quality forwards / 6,330 score rows are complete.
Independent checks pass 54,246 scalar checks and 656 Decimal reductions, maximum
5.12e-13. All 84 native primary figures are actually viewed in 21 unscaled
sheets; 42,470,400 display RGB channels are checked. Missing synthetic
crossings, real cab wires, feather/moth/grass/bark texture and colored quiet
mottle remain. Main GFX sky/building/foliage/coarse fence, both fine-mesh priors
and windows, and both JPEGs remain included. ISO100/AHD/JPEG references stay
qualitative, not exact GT.

Nineteen byte-exact final receipts and 84 native PNGs are published. The
original preparation snapshot/checkpoint250/source receipts remain byte-exact.
All nine primary owners are terminal; no experiment worker/controller remains
live. Tracked work is 8,018 component function evaluations excluding unit tests,
with zero new parent/DINO or stochastic-noise calls. Peak CUDA is 4.08 GiB in
training and 1.32 GiB in review. No worker replacement/restart, RAW/original or
dataz access occurred.

Decision: use noisy-only / 16 DN / zero peak bonus as the next noisy-head
training control, retaining V150 for stronger ADC photo restoration. Keep
V120/general and V143/explicit periodic detail as current inference choices.
README now shows two native NoADC mesh triplets with the modest gain and
missing-crossing limitation; prior ADC triplets and both real scenes remain
linked/preserved. The broader fine-detail/clean-sky objective is active and
unmet. Further work needs better estimator/spatial routing, with stronger ADC
retention; neither opening support blindly nor peak weighting is justified
by these results.

[Final report](../docs/noisy-objective-training.md) ·
[Final receipts](../docs/results/v151-noisy-objective-final-v1.json).
