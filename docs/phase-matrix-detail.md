# Matched phase-matrix pilot

V148 tests learned complex mixing of the four CFA phases after frozen V143.
**Quality interpretation remains pending.** Both fresh heads completed the fixed
1,000 updates. Four final raw/EMA endpoints have a fixed review on 798 retained
observations, including both standing GFX
scenes/priors/JPEGs and exact quiet regions beside stronger structure.

The [completed V147 diagnostic](late-spectral-detail.md) showed that opening its
local gate exposed a worse frequency proposal. Its scalar gain can select a bin,
but cannot learn a complex combination of its four phase coefficients. V148
changes that operator family while preserving the data, loss and local support
network. This is a hypothesis about estimation, not a measured gain.

The [implementation](../src/demosaic/late_spectral_matrix.py) uses a learned
complex 4×4 matrix, with conjugate frequency pairing for real-image synthesis.
It divides by a computable bound on its induced 2-norm:
`max(1, sqrt(norm1(H) * normInf(H)))`. The shared scalar diagonal is included in
this family. The bound applies per frequency bin, up to FP32 rounding; it is
neither a global RGB guarantee nor a guarantee against structure in noisy flats.
The existing constant-observation safeguard stays in place.

There are 31,409 parameters in twelve tensors, versus 30,402 for the scalar
control. All ten common tensors initialize identically. Only identifiable real
output biases are stored: a frequency-constant imaginary bias would cancel under
conjugate pairing. Both output operators start at zero and initially preserve
the parent exactly. No target/reference enters forward.

The tests independently reproduce frequency descriptors, circular convolution,
complex matrix projection and application in NumPy. They also check singular
values, finite zero-initialization gradients, coherent green-phase averaging,
constants under arbitrary finite weights, CPU RNG/device behavior, optimizer
continuation and CUDA parity. All 32 matrix/scalar component tests passed.
The averaging example establishes representational capacity, not learned quality.

The trained V147 scalar was checked on 28 cached cases covering all CFAs and
native256/384/512/768 contexts. Its legacy implementation, the refactored scalar,
and its embedding in the matrix family all produced exact pixel matches. Both
new heads then passed ten discarded CUDA updates with a genuine 8+2 reload, all
twelve parameter gradients and native512/B4 peak-memory checks. Peak allocated
CUDA memory was 4,374,891,008 bytes, about4.07GiB.

The [recipe](../configs/quality-v143-phase-matrix-v148.yaml) inherits the immutable
V147 seed, source/loss recipe, warmup, LR, clipping, EMA and 1,000-update horizon.
Both arms start fresh; the old trained V147 head is used only for engineering
checks. The same 4,000 observation IDs/noise realizations are replayed and all
input/target fingerprints match the original trace. This is not fresh validation.
The first ten cached input/parent batches are adopted; the remaining 990 parent
batches were evaluated once and cached for both arms. Parent/DINO hashes stayed
exact. Both heads receive identical cached parent/target arrays, including their
memory layout; the new scalar control is the matched comparison.

Procedural contexts remain native512 and photographs native256, with the same
90,782-photo/27-region eligibility and bin4→geometry→area2 construction. Source
images are not stretched or tiled to create larger support. The cache writes
about26GiB inside the repository, retaining the host/disk reserves. Only cached
repo/external data is read; no originals, RAW decoding or `/mnt/dataz` access.

The fixed review executes both raw/EMA endpoints on all798 retained cases with
no short-context bypass. Its independent array audit and 58 planned native
figures include four triplets per endpoint, identical ROIs/transforms, all real
windows/priors/JPEGs, flats and organic photos. Real ISO100/AHD/JPEG references
are qualitative and not exact GT. Actual native viewing and interpretation remain
required after rendering. Current V120/general and V143/explicit periodic-detail
recommendations retain their existing evidence.

The [preparation evidence](results/v148-phase-matrix-preparation-v1.json) binds
the frozen source and live-state snapshot. A preflight reporting error was fixed
before any review ran: total quiet-crop RMS is computed explicitly instead of
requesting a nonexistent helper field. The original frozen v1 postprocessor and
failure receipt are preserved; v2 passes all 32 existing mixed-parent controls.
No model, cache input, endpoint or training recipe changed in that repair.

See the [timestamped diary](../diary/2026-11-03-12-27-11-bounded-phase-mixing.md).
