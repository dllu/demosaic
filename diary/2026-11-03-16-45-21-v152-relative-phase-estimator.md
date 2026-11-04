# V152 relative-phase estimator trial

Recorded: 2026-11-03T16:45:21-08:00 (America/Los_Angeles).

Previous goal turn was progress: V151 finished all six endpoints and 84 native
figures, with modest noisy-only response/flat gains and persistent cab-mesh,
organic and quiet-region failures. Noisy-only / 16 DN / zero peak bonus is
the next noisy-head control; V150 keeps its stronger ADC photo evidence.

The next hypothesis is missing RAW/residual relative phase in the frequency
estimator. Its separate Gram descriptors are exactly invariant to reversing
the entire innovation, so the frequency matrix cannot see that reversal.
The whole model also has a RAW/parent/proposal spatial-support path; this is
not a proof of whole-model ambiguity or input-only recoverability.

V152 adds eight same-site real/imaginary observed-times-conjugate-innovation
coordinates, normalized by the geometric mean of their total powers plus
the frame-noise proxy (same finite 1e-12 descriptor floor). A zero-initialized
bias-free circular 3x3 8-to-32 convolution adds 2,304 parameters before the
original hidden SiLU. All twelve common initial tensors match; a zero adapter
exactly embeds trained native weights. This changes input evidence and
parameter count, not uniquely one causal mechanism. Existing 85 neural source
files stay byte-identical; one new research module is added. No target enters
forward. These features are not calibrated coherence or a flat guarantee.

Fresh native/control 31,409 parameters and relative 33,713 use the same old
1,000 V148 batches / 4,000 observations and V143 parents. Both have 882
supervised batches / 3,528 observations, zero ADC loss and no peak weighting,
with all 1,000 AdamW/EMA clocks retained. Data/geometry/domain weights, common
initialization, LR/schedule/clipping/EMA, FFT/band/bound and local support match.
All four final raw/EMA endpoints are fixed on 822 cases / 3,288 head calls and
72 native figures (24 repeated-cell triplets), including actual blank/quiet
errors, noisy flats, ADC photos/slopes and both real scenes/priors/windows/JPEGs.
Independent ISO100/AHD/JPEG references remain qualitative, not exact GT.
All validation/protected sources and captures/siblings remain excluded from
training. Zero new parent/DINO/noise calls, originals/RAW/dataz access.

Ten focused tests pass in 1.06 s, including independent NumPy values/complex
finite-difference gradients, descriptor alias/relative distinction, common
phase invariance, trained native embedding and learned constants across all
four CFAs, a full NumPy frequency estimator, constructor/RNG/meta handling and
finite zero-spectrum derivatives. Compatibility passes 28 contexts with 84
actual function evaluations: native, frozen base, zero-adapter and archived
V151 noisy-only pixels match. Both ten-update CUDA checks include genuine 8+2
restoration; all 25 tensors receive finite nonzero gradients. Seven supervised /
three zero-ADC steps per arm, peak 4.15 GiB. Production restarts fresh afterward.

The first controller process exited before imports/claim/scientific work due
to a relative PYTHONPATH resolved from the new cwd. Confirmed terminal PID,
exact launch/log and failure receipt are preserved. Correct absolute frozen
imports launch the valid controller, with no scientific worker replacement.
The reporting preflight passes 64 parent cases / 280 scalars, maximum 1.78e-15,
CUDA uninitialized and no new neural/noise calls. The valid training controller,
training worker and queued review controller are verified live by PID/create
time; the initial 85 complete control trace rows exactly reproduce V151.
Trained quality and actual native viewing remain pending; the broad goal is
active and unmet.

[Protocol](../docs/relative-phase-estimator.md).

Checkpoint/readiness update: 2026-11-03T16:50:44-08:00 (America/Los_Angeles).
Checkpoint 250 contains 25 finite Adam states and finite raw/EMA tensors; native
raw/EMA/Adam exactly reproduce V151 noisy-only. The preparation snapshot binds
397 complete exact-control rows and 46 ADC zero-loss/zero-norm rows per arm,
with all three current owners confirmed live. Eleven byte-exact receipt copies
and fourteen source texts preserve readiness, including the pre-claim bootstrap
failure, with 86 frozen neural hashes and unchanged previous 85. Quality remains
unmeasured. [Preparation evidence](../docs/results/v152-relative-phase-preparation-v1.json).
