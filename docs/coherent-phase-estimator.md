# Matched coherent CFA estimation trial

V149 tests explicit CFA phase transport and green common/difference evidence
against a fresh native-matrix control. **Trained quality remains unmeasured.**
All three fresh heads train for a fixed 1,000 updates on the existing V148 cache.
Six final raw/EMA endpoints have a fixed review on all 798 retained cases,
including actual blank errors, the mixed quiet controls and both standing GFX
scenes/priors/windows/JPEGs. This is an adaptive reused cohort, not fresh
independent validation.

The [previous diagnostic](spectral-capacity-oracle.md) established substantial
GT-informed per-bin amplitude headroom, without proving input recoverability or
shared-network representability. It also exposed a false lattice in an exact
quiet region beside stripes. The next test improves input-derived evidence
and support jointly, while keeping the native-coordinate norm budget fixed.

## Three fresh arms

| Arm | Parameters | Change |
| --- | ---: | --- |
| Native matrix control |31,409|V148 estimator/support and unchanged native-coordinate bound|
| Aligned matrix |31,409|Estimate in known CFA-transported R/Gsum/Gdiff/B coordinates; return to physical slots before applying the original conjugate/norm bound|
| Aligned with coherence context |33,353|Same aligned estimator; append nine raw-derived energy/contrast summaries to support, at packed scales9/33/129|

For a packed frequency f, native site offsets are `(0,0),(0,1),(1,0),(1,1)`.
Multiplication by `exp(-i*pi*(fy*dy+fx*dx))` aligns the physical sampling offsets.
A real orthogonal rotation orders red/blue and forms the sum/difference of the
two green sites. An ideal periodic carrier then occupies the green-common
channel. This is an exact coordinate statement before windowing; tapering,
affine removal and boundaries make finite-frame alignment approximate.
Packed Nyquist fractional shifts need not have real-image symmetry, but the
existing output band is zero there and final native conjugate pairing remains
explicit.

The estimated complex matrix is transformed back to native CFA coordinates
before the original `sqrt(norm1*normInf)` projection. That gauge is not invariant
to a basis change, so applying it in the new basis would change the native
budget. The native per-bin bound and scalar diagonal family are retained, up to
FP32 rounding. This is not a global nonlinear/RGB or noisy-flat guarantee.
The shared neural function still changes through the input coordinates.

The contextual arm synthesizes band-limited observed green common/difference
fields with the existing overlap geometry. Each packed scale provides
`log1p(common_energy/raw_variance)`, `log1p(difference_energy/raw_variance)` and a
signed energy contrast. Separable averages provide local and wider summaries
without quadratic large-kernel cost. These are uncalibrated features, not signal
probabilities or noise whitening. Basis noise diagonals are transformed; the
unequal-green off-diagonal covariance is not a calibrated full-noise model.
No target, ISO100 reference, JPEG or parent pixel enters the nine added features.
The original support inputs still include the supplied frozen parent.

Both estimators and support networks train together. All twelve native/aligned
initial parameter tensors match exactly. The context arm copies all existing
weights, preserves the first28 local-input columns and initializes the new nine
columns to zero. All frequency outputs start zero, preserving the parent at the
first update. Constants remain inactive under learned finite arithmetic.

## Engineering and fixed evaluation

All 53 scalar/matrix/coherent component tests passed. The new tests independently
check physical carrier phase, unitary matrices, native-coordinate gain math,
local overlap synthesis and spatial averages in NumPy. They cover all four CFAs,
constants, CPU RNG/meta-device behavior, CPU FP32/BF16 optimizer continuation,
CUDA parity and all twelve parameter gradients.

The local-feature hook is a refactor of the old support concatenation. The
trained V148 matrix's old forward, the new forward and the archived pixels match
exactly on 28 cases covering all CFAs and native256/384/512/768 contexts. All three
heads then pass ten discarded CUDA updates with genuine8+2 optimizer reload.
Every tensor and the new context-input columns receive nonzero finite gradients;
peak allocated CUDA is4.50GiB. Smoke weights are discarded before production.

The [recipe](../configs/quality-v143-coherent-phase-v149.yaml) inherits V147/V148's
loss, source distribution, seed, geometry, schedule, clipping, EMA and1k horizon.
It adopts the existing1,000 batches/4,000 observation-parent-target arrays
without new noise construction, parent or DINO calls. Native control is the
matched comparison, with the older V148 raw/EMA states available for exact
replay checks. No photograph is stretched or tiled to create more context.
The inherited source pool/region eligibility remains90,782/27; the sixteen
reviewed validation photos and protected captures/siblings remain excluded.

The queued review fixes all six final endpoints on798 cases and66 native
figures, including24 repeated-cell triplets. Input/ROI/display transforms stay
identical across methods, with no resized crop pixels. New reporting includes
actual blank/DC/spatial errors alongside correction energy. A40-parent preflight
checks the quiet/blank formulas and existing native templates before any quality
inference. Real ISO100/AHD/JPEG references differ in aperture/exposure/moving
subjects and remain qualitative, not exactGT. All original media stays read only;
only repo/external cached arrays are used, with no RAW decoding or dataz access.

The [preparation evidence](results/v149-coherent-phase-preparation-v1.json) binds
source, plans, engineering receipts and an active-state snapshot. An initial
preparer assumed an optional `output_shape` metadata field; it stopped before
creating the trial or doing GPU work. The corrected preparer reads cached NPY
headers for the storage estimate; the failed source/receipt are preserved.
The model/data/scientific design did not change.

The broader fine-detail/clean-sky goal remains active. Current
[model recommendations](current-model.md) retain their existing quality evidence.
See the [timestamped diary](../diary/2026-11-03-13-36-40-v149-coherent-phase-trial.md).
