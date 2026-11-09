# Physical cross-scale support for CFA waves (V200)

The [V199 gate diagnostic](cfa-wave-gate-diagnostic.md) leaves building fringes
and false flat/photo ripples under shared RGB and positive-only gates. The next
prototype adds **physical amplitude/phase agreement between local windows** to
the readout, preserving V198's measured color basis and frozen V195 anchor.
It is an engineering implementation; trained quality remains unmeasured.

V198 already compares two green phases within each window. Its 24 context
channels do not directly compare a color's physical fitted amplitude between
65-, 33- and 17-pixel packed windows. The new twelve channels describe that
agreement for R, averaged G and B, at the existing fixed input-derived bins.
They can expose local inconsistency without supplying an invented synthesis
wave. They can also agree on noise, edges or anchor errors; no flat-safety claim
follows from their construction.

## Physical fit and nominal covariance

For each actual CFA phase, each clipped local box removes a constant and two
linear coordinates from the carrier. Let the resulting real wave columns be
`Q = [cos(theta), -sin(theta)]` after this affine projection. Then

```text
G = Q^T Q
a = G† Q^T field
H = Q^T diag(v_RAW) Q
Cov_nominal(a) = G† H G†
```

The complex amplitude is `a[0] + i*a[1]`. Integral moments compute both the
trace `sum(v*abs(q)^2)` and complex pseudo-variance `sum(v*q*q)`, which recover
all four entries of H. A scalar trace divided by the Gram is insufficient for
heteroscedastic noise. The eigenvalue cutoff is the existing numerical
`1e-10 * box_area`, including rank-one Nyquist bins; it is not a detection or
confidence threshold. No learnable covariance or target enters this fit.

Measured amplitudes are transported from the actual CFA offsets to canonical
native phase. Red and blue use their own measurements; green averages its two
phases. Under the nominal independent-RAW model, green's center covariance
trace is `(trace_G1 + trace_G2)/4`. Canonical phase rotation preserves trace.

Interpolation uses actual grid centers, including the last irregular gap.
Overlapping boxes have correlated errors. For nonnegative bilinear weights,

```text
nu(pixel) = (sum_i weight_i * sqrt(center_trace_i))^2
```

bounds the interpolated trace in the fixed linear independent-RAW model, by
Cauchy-Schwarz. It is **not exact interpolated variance** and does not assume
independent boxes. The direct-operator test includes their shared samples and
checks a strict gap between the exact variance and this bound.

Selection reuses these samples, and the anchor is a function of RAW. Neither
its error covariance nor its correlation with RAW is modeled here. Thus even
the nominal bound is **not calibrated innovation confidence**, a false-positive
rate or an independent holdout test.

## Twelve support coordinates and the readout

For large/small canonical amplitudes and nominal trace bounds:

```text
Z(L,S) = 2*A_L*conj(A_S)
         / (abs(A_L)^2 + abs(A_S)^2 + nu_L + nu_S + (1/65535)^2)
```

Its modulus is at most one. Equal strong waves approach +1, opposite phases
approach −1, and the nominal powers attenuate weak amplitudes. Joint carrier
phase rotation cancels. This is descriptive amplitude/phase agreement rather
than the covariance of a cross-scale difference.

For each selected bin, new channel order is:

| Coordinates | Meaning |
| --- | --- |
| 0…2 | Real RGB agreement, 65 with 33 |
| 3…5 | Imaginary RGB agreement, 65 with 33 |
| 6…8 | Real RGB agreement, 65 with 17 |
| 9…11 | Imaginary RGB agreement, 65 with 17 |

These append to the unchanged 24 V198 coordinates. The head becomes
**36→16→3, 643 parameters in four tensors**, adding 192 parameters. The old 24
input columns and hidden biases keep their original initialization; extra
columns start at zero, as do final gates. The 193 trained V195 Whole EMA anchor
tensors remain frozen, with 197 full-state tensors. Existing source files and
checkpoints remain unchanged.

Selection stays at eight pooled innovation bins in native band 1/64…1/3.
The physical 65-window RGB synthesis basis, explicit native subpixel transport,
sum across bins and real tanh gates in [−1,1] remain. Support cannot synthesize
red/blue waves from green, and the correction is not multiplied by output
sigma. Zero-noise pixels retain the anchor exactly.

Additional features and 192 parameters change together. A future comparison
tests this combined architecture, not covariance or cross-scale evidence in
isolation. The present implementation remeasures amplitudes at three scales;
its extra computation has not been benchmarked on a complete 100MP frame.

## Engineering checks and quality requirements

All **34 focused CPU checks** pass. They cover direct affine-QR amplitudes and
every nominal covariance entry on heteroscedastic rectangular fields, singular
DC/Nyquist ranks, affine invariance, variance scaling/zero variance, all four
Bayer layouts and both dtypes, native wave-basis agreement, overlap-aware
interpolation bounds, phase/sign behavior and invalid inputs. Wrapper tests
cover exact initial anchor output, unchanged old contexts/basis, isolated
learning through extra columns, zero-noise routing, RNG and strict states.

GPU admission passes eight actual bit-exact anchor parities, seven
CPU/GPU feature comparisons (325,582,848 context and 54,263,808 physical-wave
coordinates), all three scales' nominal covariance checks (4,993,152 entries),
and seven nonzero readout checks with active extra input columns. Two
training-only mesh/mixed updates match independent CPU head gradients. All 192
extra input weights receive nonzero gradients on update two. Actual strict
model/Adam/EMA/CPU-CUDA RNG restoration after update one precedes update two.
The original admission owner is terminal; peak CUDA allocation is 9.747 GiB.
The independent CPU inspector checks four raw/EMA states, 772 unchanged anchor
tensors and both Adam states without CUDA initialization.
[Verified engineering evidence](results/v200-scale-supported-CFA-preparation-v1.json).
Device comparisons use the same frozen implementation on CPU and GPU; the
independent mathematical reference is the direct-QR test implementation.

A fresh **900-update trial has been launched** from the retained V195 anchor,
using the same 1,000 cached rows, 3,600 noisy images, 100 ADC skips, ten-term
Whole objective, pair units, masks, LR/WD/clip and seed 202611080198 as V198.
Adam and EMA start at zero, independently of the probes. The real row-eight
checkpoint restoration passes and continues at row nine without repeating
earlier forwards. Five factored snapshots, a full independent training audit,
both endpoints/all 822 quality cases and native comparisons are required.
Quality is pending; training loss is not restoration-quality evidence.

The GPU check uses retained cached inputs and training-only mesh/mixed update
probes; protected sky, cab and building inputs are parity-only. Probe snapshots
are never training initializers. No new photos/noise draws, RAW decoding,
original-media/dataz access or external writes occur. The full trial budgets
2 GiB local storage above a 40 GiB reserve and reuses earlier data in place.

An improved model still requires the full matched detail/absent/quiet/fresh-flat/
photo suite and native noisy/restored/GT triplets, plus both held-out GFX scenes.
The real DSCF3879/3880 main-scene sky/building/foliage/coarse fence and
DSCF3842/3835 fine cab mesh, both cab ROIs/noise profiles and both JPEGs remain
required qualitative checks. Their independent ISO100/AHD/JPEG references are
not exact GT. Both capture families, JPEGs and siblings stay out of training.

Current useful trained choices and their observed costs remain in the
[V198 comparison](cfa-innovation-wave-comparison.md) and
[model guide](current-model.md). Fine real crossings and flat safety remain
unresolved.
