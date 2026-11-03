# Target-informed spectral capacity diagnostic

Recorded: 2026-11-03T12:57:23-08:00 (America/Los_Angeles).


The previous goal turn completed V148's matched trial and native review, giving
negative quality evidence. This turn tests whether the post-parent spectral
operator itself lacks capacity before another architecture/training change.

Prepared a fixed target-informed diagnostic on all792 constructed-target cases.
All6 real contexts are excluded from oracle calculation because their references
are qualitative, not exactGT. Eight modes probe signed scalar, feasible bounded
matrix, relaxedL2, band-only/unbanded residual, frozen/full support and global
image-alpha behavior. Every oracle uses GT inside its output and independent
per-bin matrices relax the shared neural parameterization. This is not an
inference improvement or a proof of noisy-input recoverability: with GT, a matrix
can rotate noise toward a known answer.

Six final oracle-math tests pass in1.46s, including independent NumPy equations,
singular values, zeros, full-image line search and CPU/CUDA parity. Preparationv1
stopped on an absent optional `reference_role` key before any plan/inference;
its source/receipt are preserved. V2 checks explicit constructed-case kinds and
saved NPZ target fields. The corrected model/operator recipe is frozen before
collection. No preexisting scientific source or receipt was changed.

The component replayed all792 original matrix-raw predictions exactly, then
produced6336 GT-using arrays. No training, parent/DINO calls, noise construction
or RAW decoding occurred. All84 frozen neural files and parameter state stay
exact; peak allocatedCUDA811,386,880 bytes. Internal/external reserves and
52/32GiB RAM admission/runtime checks pass. Both standing GFX scenes/siblings
remain held out, with original files untouched and no dataz access.

Mean mesh response .022021 parent/.020022 learned matrix becomes .716526 under
the feasible GT matrix/full witness; frozen support limits it to .133007.
GT scalar/full reaches .289746. Mesh RMS9.11124 parent becomes6.10776 matrix/full
and3.65880 unbanded target residual. This establishes substantial headroom in
the relaxed per-bin operator, without showing that the shared network can learn
these coefficients. Gate opening on the existing learned proposal remains
harmful, as V147 already showed.

GT matrix/full reduces faint retained512 photo RMS33.96375→19.21751 and band
error .824639→.447391; unbanded residual gives9.90891/.125849. Native feathers,
moth, grass and branch texture return, with remaining checker/color/ringing
along boundaries. Native512 ISO6400 flat RMS18.54681→15.77383 but coarseblock32
13.44056→13.36192 barely improves; excluded low frequencies/affine terms and
fixed Malvar reconstruction leave important restrictions.

Correction energy alone is not a hallucination measure. In exact blank masks
inside present meshes, GT matrix/full changes pixels by RMS2.47963 yet reduces
actual blank RMS5.52332→5.01548. The learned matrix changes .63867 and worsens
actual error to5.55579. Absent GT matrix/full also improves5.23791→4.70707 despite
nonzero corrections. Added-change metrics should be retained with actual
blank/DC/spatial errors, rather than serving as a blanket prohibition on useful
denoising changes.

A separate important failure appears beside strong stripes. In the exact quiet
ROI of the RGGB ISO6400 striped example, GT matrix/full raises error3.52814→5.21476
while whole-scene RMS drops58.85471→34.77377. ISO12800 quiet6.95183→8.62557 while
whole-scene87.10782→45.06555. The GT-derived global RGB line search chooses1 on
both and retains a clear false diagonal lattice. This is a concrete counterexample
to treating per-bin contraction or whole-image improvement as local flat safety.
Frozen support reduces the lattice. The band-only/unbanded oracle controls
show that frequency-dependent capping and shared synthesis also matter.

The independent scorer/auditor checks9288 rows,61664 scalars and812 Decimal
reductions, maximum difference1.59e-12;2952 archived baseline bindings/metrics
match V148. A separate NumPy64 implementation independently rebuilds affine/STFT,
noise-power cap, scalar/matrix witnesses, overlap synthesis and signed Malvar
on8 fixed cases covering4CFAs and photo/flat/mixed types:32 reconstructions,
maximum difference1.17e-8 cameraRGB. Both its first passing source/receipt and
lint-clean v2 are preserved. Region/line audit covers all792 cases plus6144 mesh
blank rows, including FP32-aware global-alpha checks.

Actually viewed all12 original native sheets plus2 individual quiet extracts:
40 GT-using figures and8 byte-exact unchanged realV148 boards. Original rendering
checks34,867,200 RGB channels; the two close views repeat768,000 channels exactly.
All160x160 crop pixels remain unscaled with original coordinates/transforms.
The real sky/building/foliage/fence and extra mesh both priors/windows/JPEGs remain
the previous V148 evidence, with ISO100/AHD/JPEG references explicitly notGT.
All4 recorded primary workers are terminal. The detached component exitcode was
not observed; its terminal owner identity and completed result were separately
verified. All3 analysis child exits were observed0.

Published the current report, native assets, byte-exact receipts and scoped
source bundles. This changes the next action: simplify input-derived coherent
phase evidence, then improve spatial support jointly, instead of lifting the
norm budget or blindly opening the learned gate. Explicit CFA phase transport
and green common/difference coordinates are a concrete next estimator basis.
The broad weak-detail/clean-sky objective remains active and unmet.

[Report](../docs/spectral-capacity-oracle.md) ·
[Evidence](../docs/results/v148-spectral-capacity-v1.json) ·
[Native manifest](../docs/images/v148-spectral-capacity-v1/manifest-v1.json).
