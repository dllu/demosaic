# Cross-frequency phase inputs: V163

V163 tests whether cross-frequency phase information can recover fine detail
while retaining V162's flat-target anchor. Both 1,000-step heads are complete:
93 finite final Adam states, four strict CPU endpoint loads, exact V162
control trace/raw/EMA/Adam states and 1,000 inherited audited masks pass.
Full quality review and native comparisons are pending. V161 remains the stronger learned mesh
prototype, and V162 remains the measured grain-reduction implementation. Their
strengths and costs are documented in the [current model guide](current-model.md).

The frequency gain in V161/V162 uses power, same-frequency Gram and relative
cross-spectrum descriptors, plus dyadic context derived from those descriptors.
A common phase rotation applied to observed RAW and innovation at each frequency
leaves that conditioning unchanged. The existing spatial and support paths can
see spatial phase. This proposal addresses the narrower frequency-conditioning
limitation.

The new input uses each of four packed RAW phases separately. For observed RAW
and innovation, define `u(w) = F(w) / sqrt(sum_phase |F(w)|² + sum_phase noise)`,
with the inherited arithmetic floor of 1e-12. Four complex products
`u(w)² conj(u(2w mod S))` supply eight real coordinates per spectrum, sixteen in
total. A zero-initialized, bias-free 16→32 projection enters before the inherited
frequency SiLU. It adds 512 parameters: control 124,397 / 46 tensors; candidate
124,909 / 47 tensors. Existing matrix bounds, conjugate projection, support,
band limits and the direct RGB path remain. Extra capacity and compute are part
of the intervention; this is not an equal-capacity causal contrast.

Each complex product has magnitude at most one in exact arithmetic. Integer
packed-grid circular-shift phase ramps cancel algebraically. Tapering and
detrending prevent interpreting this as full-network translation invariance;
fractional and CFA-exchanging shifts have no such guarantee. A single noisy
third-order product is neither calibrated confidence nor an unbiased signal
estimate. Poisson skew, windowing and noise-dependent normalization matter.

[Recent primary-source reading](results/harmonic-phase-research-20261107-v1.json)
motivates investigating phase coupling. The cited bispectrum theory assumes
repeated signals and Gaussian noise; the other work studies RGB enhancement.
Neither establishes fidelity for Poisson/read-noise RAW. No paper code, weights,
pseudo-infrared prior or phase-inversion algorithm is adopted.

All **180 CPU checks pass**, including 24 new checks. Independent NumPy loops
verify values and complete complex-spectrum/shared-noise adjoints, including
doubled-frequency alias accumulation. Tests also cover descriptor collisions,
integer shifts, conjugacy, exact embedding of nonzero inherited heads and their
common parameter gradients, batch isolation, active-path constants and all 47
parameter tensors receiving gradients.

An [algebraic witness on the trained V162 EMA head](results/v163-phase-information-witness-v2.json)
keeps all inherited conditioning and its actual frequency gain exactly equal
under a conjugate-bin sign flip; the new features differ by up to 0.3869085.
This is a representation test on artificial spectra, not a photo-quality result.
Its [first serializer failure](results/v163-phase-information-witness-failure-v1.json)
is preserved: complex gains needed real/imaginary coordinates for the existing
finite-real-array fingerprint helper. The failed and corrected witnesses used
four separate CPU frequency-gain calls, zero root-model forwards and no CUDA.
The initial conjugacy test also required an unjustified exact FFT equality;
its 1.4e-16 discrepancy is now covered by an FP64 tolerance. Model arithmetic
was unchanged by either correction.

Both heads train fresh on the same retained 1,000 V160 batches of four. V162's
flat-target weight 0.25, paired-response loss, all base losses, initialization
of shared tensors, LR, AdamW, clipping and EMA clocks stay fixed. All 88 earlier
neural modules remain byte-identical. Control must reproduce the V162 candidate's
1,000 trace rows, raw/EMA/Adam states and 1,644 actual predictions before storage
adoption. Four strict CPU endpoint loads and 93 finite final Adam states are
required. The extra phase adapter starts at zero and must exactly embed the
trained V162 head on 28 archived contexts before training.

The fixed review covers all 822 cases at both raw/EMA endpoints of both heads:
3,288 actual calls, 1,644 new main prediction arrays and 1,644 actual control
replays. A prospectively fixed twelve-input phase-adapter removal diagnostic
adds 48 calls and 24 off arrays, replaying on outputs exactly and restoring
weights. It measures output displacement, not accuracy or an isolated training
cause. Including parity and discarded/restored smoke, the plan is **5,412 root
calls / 11,472 head images**, plus ten leaf-output CUDA loss backwards and the
four separate CPU witness frequency-gain calls. Tests are separate.

Seventy-two planned native images include 24 noisy/denoised/exact-GT triplets.
Seven retained comparator columns preserve V156 raw, V157/V158/V159 EMA,
V160 ordinary/paired EMA and V161 EMA alongside current controls. All methods
share source ROIs and display transforms; crop pixels are never resized.
The 58,137,600 planned native RGB channels must match independent rendering.
Both standing GFX scenes, both cab priors/windows, foliage, coarse fence,
building, sky and native camera JPEGs remain included. ISO100 captures differ
in aperture, shutter and moving subjects: qualitative references, not exact GT.
Protected captures, JPEGs, siblings and held-out Commons sources stay out of
training. No original RAW, source drive, `/mnt/dataz`, new parent/DINO call,
source construction or noise sampling is required.

The original reviewer stopped after 268 successful control calls when its
combined disk guard failed. The log records no per-disk snapshot, so the failing
disk is unproven. The original reviewer and queue are terminal. Full checks of
input, parent, output, journal and exported-weight bytes verified all 268 calls;
an explicit continuation adopts them and evaluates only the missing 3,020 main
review calls. No completed model call or training run is repeated. The fixed
822 cases, four endpoints, neural arithmetic, data, displays and 5,412 planned
scientific root calls stay unchanged. One scientific review-stage failure is
recorded; all failed sources, receipts, logs and journals remain preserved.
[Training validation, failure and continuation evidence](results/v163-review-continuation-v2.json).

The study uses a 12 GiB CUDA quota, 52 GiB launch / 32 GiB runtime RAM floor,
and initial local/external reserves of 60/148 GiB. The review continuation
uses 58/148 GiB, a 0.25 GiB bound on remaining local artifacts and a 0.5 GiB
projection margin. All prediction arrays remain external. Older experiment bytes are retained. Exact original process identities
are monitored until terminal; timeouts do not authorize restarting workers.

[Prospective LA diary](../diary/2026-11-07-06-41-03-v163-harmonic-phase.md) ·
[Actual preparation evidence](results/v163-harmonic-phase-preparation-v1.json) ·
[Training recipe](../configs/quality-v143-harmonic-phase-v163.yaml) ·
[Architecture](../src/demosaic/late_harmonic_phase.py) ·
[Tests](../tests/test_late_harmonic_phase.py).
