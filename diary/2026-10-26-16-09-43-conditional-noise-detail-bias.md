# Conditional noise bias in weak photographic detail

Recorded: 2026-10-26T16:09:43-07:00 (America/Los_Angeles).

Previous goal turn was progress: new V120/V121 camera-reference predictions,
current native comparisons and independently verified V122 training completion,
committed/pushed asdbaf164. Started by checking the actual original controller,
V123 worker and four downstream owner handles; all were live. V123 was at300.

The current ADC-floor calibration study already covers narrow dark signal
support, corrected clipping and deep-shadow extrapolation. Did not repeat its
240-input study, relax reliability thresholds, fit the GFX to model outputs or
change inference priors. The useful next unknown was whether the weak-detail
error persists across independent noise realizations of the same target.

Prepared a finite new conditional-noise experiment with two retained Commons
targets (bark, raccoon fur) and two previously selected camera-linear reference
contexts (GFX5002 grass/root, Leica1951 lower wood rail). The Commons targets
are exact synthetic supervision; native estimates retain reduced source noise
and optics and are not exact noiselessGT. No source/ROI was selected using the
new predictions. Native256 contexts, central160ROI[48,48,160,160], shared source
WB/matrix/exposure1. All4CFAs,8 new independent draws/layout, ISO12800 prior
shot.00256/read.0000262144, ADC16/black.03. Seed is derived from a fixed task key,
case/CFA/draw; all128 seeds and noisy packed fingerprints are distinct.

New input generation is explicit:128 Poisson/Gaussian/ADC observations, shared
across V120/V117. Actual preparation forbids all neural Module calls, preserves
global Torch RNG and leaves CUDA uninitialized. Independently checked8,388,608
variance-map values against NumPy arithmetic. Original stored inputs and targets
remain unchanged. The neural source/official frozen encoder/20k EMA identity
and all five actual arguments are verified before every forward. Neither
model's state changes. New root/encoder budget is256, referenceNN/RAW/training0.
No original primary, camera, GFX or mesh inference was repeated.

Run root:
`.cache/current-quality-20261023-v1/conditional-noise-response-v1`.
Prospective plan SHA256:
`abee2a2be5f60c4bd048dc3cf6ac6b0af79d7459080d3a8e6a017b1f43646093`.
The run completed its exact256 root and encoder calls and all32 eight-draw
groups. CUDA cap12GiB, runtime RAM32GiB, internal96/external208GiB reserves;
no timing ranking during V123. The original training and downstream plans/code
were not edited, signaled, restarted or extended.

Added the small pure-NumPy `conditional_bias.error_moments` helper. The finite
sample mean error contains output variance/K, so subtract that term to estimate
conditional squared bias. Preserve negative finite-sample estimates. Empirical
per-draw MSE equals corrected bias plus unbiased sample output variance. Eight
focused tests check pairwise cross-error equivalence, negative estimates,
deterministic bias/exact targets and invalid groups. All pass; Ruff passes.

Actual independent pairwise cross-error products replay all32 camera groups
within5.421e-20. Maximum MSE decomposition identity error is2.168e-19. Analyze
all CFAs separately then average, without pretending they are additional draws
of one layout. Four deliberately selected targets are not population evidence
or training-seed repeats. A biased posterior estimate can trade mean error for
lower variance; this decomposition alone establishes no loss or architecture
cause and no promise of a better single-capture method.

For V120, camera-RGB whole-ROI estimated bias fractions are27.08%bark,
45.89%fur,50.36%grass and46.69%wood. Local linear-luma16px DCT band1/8–1/3,
reference luma.02–.9/RMS>=1e-5 and GT-only contrast grouping gives:

- Bark>=20% contrast:96 blocks, gain.97095, bias share12.11%.
- Fur0–2% contrast:7 blocks, gain.31704, bias share84.56%.
- Grass2–5% contrast:3 blocks, gain.59263, bias share42.34%.
- Wood2–5% contrast:9 blocks, gain.63563, bias share69.70%.

V117 is similar: gains.96863/.31945/.59416/.62425 and bias shares
12.52/83.21/41.76/71.71%. Strong bark is largely variance-limited, while the
selected faint fur/wood groups have substantial persistent error. Native source
noise can contribute to the reference bands; no exact real-detail loss claim.

Actually viewed all four six-cell native boards. Mean8 reduces visible noise,
but fine fur, grass/background and some wood irregularity remain soft; strong
bark retains coherent texture. Mean8 uses eight independently noisy observations
and is unavailable from one capture. All figures and metadata label that
diagnostic explicitly; it is neither a new inference mode nor a model gain.
Published the four boards and eight single/mean triplets, with actual draw0
and exact Commons GT for bark/fur. All3,686,400 panel channels independently
match retained arrays/means under explicit-channel NumPy64 display arithmetic.
No resizing. Sources, original target metadata, noise seeds, checkpoint hashes,
WB/matrix and exposure are retained; original pending-view receipts stay intact.

Public report:`docs/conditional-noise-response.md`.
Result:`docs/results/conditional-noise-response-v1.json`, SHA256
`2ae273c74ebaeab6483b2ef2e4c16c9e6cecfdc94d87b5ab43157ee31ad58c4c`.
Publication verification checks37 original/public files,165 current-doc links
and all distinct draw identities. Receipt:
`docs/results/conditional-noise-response-publication-v1.json`, SHA256
`e1b3bfd1abb18f456fd60eec4986aad5227bf4b26786f13a8f085f50176e1ced`.
Updated current model/training/index/noise-conditioning guides, correcting the
last V114-as-current wording while preserving V104's actual historical strength
results. V120 selection, primary scores/plots and all existing outputs stay put.

Concrete next hypothesis: a convex.25 conditional-mean reconstruction term
versus a matched zero-weight control, both using two independent corruptions
of each clean target. For squared error the mean term changes bias/variance
weighting; actual Charbonnier/rendered/edge behavior still needs implementation,
training and quality tests. Use V120 and prepared90784/twenty-region data; pair
simulated Commons/native targets only, preserve real-paired single-input steps,
and load only the unique contexts actually needed. No new training loss or
model was implemented/trained in this turn. This is a specific follow-up to
the new measured bias, not a reason to reduce conditioning globally or freeze
current recommendations. Active V123 and its original full review continue.

Final live-owner check: V123 at950, worker993796/create1793054390.74 and original
controller4066396/create1792992904.87 both live. Quality4073072, audit4073170,
report889938 and mesh889990 remain live in expected dependency waits. Available
RAM66.15GiB; internal/external free648.86/222.94GiB. V122 remains completed20k,
with image quality unmeasured. Future90784/twenty-region data remains untrained.
State-of-the-art, broad real-photo superiority and100MP/10s remain unproven;
the full goal remains active.
