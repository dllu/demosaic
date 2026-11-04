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

## Completed review — 2026-11-03T17:14:44-08:00 (America/Los_Angeles)

Both heads finish 1,000 updates with all 25 finite Adam states. Control complete
trace/raw/EMA/Adam and all 1,644 prediction arrays exactly reproduce V151
noisy-only. Both have 882 supervised batches and 118 zero-loss/zero-norm ADC
steps with all optimizer/EMA clocks retained; no noisy step clips.

Relative raw/EMA mean mesh response is .02394498/.02314068: +1.41%/+1.27%
versus matched control, +8.74%/+5.09% versus V143, still only 2.39%/2.31%
of exact constructed GT. Present RMS improves .295%/.251% over V143. Actual
blank RMS improves .006%/.060% despite more added correction; change energy
is not a hallucination metric. Absent RMS improves .025%/.072%.

Native512 noisy-flat full RMS improves .141–.205% over V143, another
.035–.048% versus control, with tiny/mixed coarse changes and broad colored
mottle still visible. All 48 constant ADC observations stay exactly at parent
under all four endpoints (192 arrays). Relative raw photo full RMS improves
.0056–.0154% over V143; EMA is mixed. Band-error means fall versus control,
but all four groups' band responses fall further and native texture remains
soft. This is not useful new natural-texture recovery.

Strong-pattern whole RMS improves .271–.488% over V143, but exact quiet RMS
worsens .334–.834%, more than control's .154–.385%; quiet spatial RMS rises
.432–1.117%. Additional fine grain accompanies unchanged large blobs in
diagnostic 40x views. ADC photo RMS improves .302–.324% versus V143, smaller
than V150's 3.06%, with reduced band response. ADC sloped full RMS improves
.510–.555%, while coarse block32 regresses .719–.933%, more than control.
Smooth central crops do not erase that wider-field weakness.

Mesh mean support rises to .479/.464 from .440/.424; proposal coefficient
RMS rises slightly to 1.158e-5/1.049e-5. Present/absent support means are nearly
identical. Both proposal and support change, and parameter count differs;
there is no unique causal proof that relative phase solves a bottleneck or
that larger mean support is selective detection.

All 822 cases, 3,288 quality forwards, 4,686 score rows, 72 native primary figures
and 18 unscaled sheets are complete. Actual native viewing finds no convincing
new crossing family, real cab wires, feather/moth/grass/bark or bird/branch
texture. Both standing real scenes, mesh priors/windows and camera JPEGs stay
included; ISO100/AHD/JPEG references remain qualitative, not exact GT.
Independent checks pass 40,210 scalars/476 Decimal reductions (max 4.55e-13),
with 32,332,800 display RGB channels checked. Nine scientific owners plus the
failed pre-claim bootstrap are terminal; no experiment jobs remain live.
Peak CUDA 4.15 GiB training / 1.45 GiB review. Total tracked component evaluations
5,392 excludes unit tests, with zero new parent/DINO or stochastic-noise calls.

The first publisher retained a lowercase V151 version in output/preparation
paths and stopped before final-index creation. All 18 copied receipts, 72 PNGs
and the manifest (91 artifact byte bindings), plus failed source, are preserved
under owned failure evidence. Corrected V152 publication copies 19 receipts
including that failure record and all 72 native PNGs. Model/input/metric/image
pixels and frozen scientific code did not change; no scientific worker restart
or replacement. Original preparation receipts/snapshot 397/checkpoint 250 remain
byte-exact. No original/RAW/dataz access occurred.

Decision: retain relative-phase inputs as a useful next frequency-estimator
prototype, with V151 as the quieter matched comparator and V150 for stronger
ADC photo restoration. This is a mixed improvement, not a new general inference
recommendation. Next work must address local support/quiet errors and preserve
natural-detail response, with current learned proposals tested directly rather
than assuming that the older V147 gate probe transfers unchanged. README now
shows two native relative raw mesh triplets with small gains and the missing
crossing/quiet limitations; all prior model/image evidence remains preserved.
The full fine-detail/clean-sky objective stays active and unmet.

[Final report](../docs/relative-phase-estimator.md) ·
[Final receipts](../docs/results/v152-relative-phase-final-v1.json).
