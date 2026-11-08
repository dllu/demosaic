# Color-grounded innovation readout (V198)

**The engineering checks pass and full training has launched. Image quality is
unmeasured.** This candidate addresses a weakness in the completed
[V197 comparison](innovation-wave-comparison.md): stronger faint mesh modulation
coexists with a pronounced red/cyan building artifact and extra flat-field waves.
The real cab crossings remain incomplete. V197's gains and costs, V195/V187's
lower-error strengths, and the general V120 Small recommendation remain current.

V197 measures two green phases and learns complex mixing weights into all three
RGB channels. That permits red/blue correction waves without corresponding
red/blue measurements. This is a structural observation, not proof that it caused
the observed building failure. V198 tests a different representation: each RGB
correction uses measurements of that color, with a bounded real gain.

## Measurements and synthesis

`LateCFAInnovationWaveDetail` retains all **193 trained V195 Whole EMA tensors**
and adds a fresh **451-parameter, four-tensor head**. Full state still has 197
tensors. The new head starts at zero output with fresh Adam/EMA clocks; it does
not inherit V197's artifact-producing head. Its anchor separately retains the
V187 900-update and V195 900-update history.

Selection is the existing input-only pooled two-green innovation selector:
observed RAW minus the frozen anchor sampled at the actual CFA locations,
eight bins in the native 1/64…1/3 band. Selection still reuses both green phases;
neither is an independent confidence holdout. No target enters the forward pass.

At each selected bin, local 65px packed boxes fit all **four actual CFA phases**
to an affine plane plus real cosine/sine. The two wave coordinates are solved
after removing the affine nuisance space. Eigenvalues at or below `1e-10` times
box area are dropped for numerical rank, including an unmeasurable Nyquist
quadrature. This threshold does not detect signal or establish confidence.

The measured complex amplitude is `cosine coefficient - i * sine coefficient`.
Actual CFA offsets are removed, complex amplitudes are interpolated at the
actual box centers, and native subpixel phase is restored explicitly. Red and
blue each use their own CFA phase; green averages its two phase estimates.
Physical wave amplitudes retain camera-linear units.

The shared `24 -> 16 -> 3` pointwise head produces one real `tanh` gain per color
and bin, bounded to `[-1, 1]`. A signed gain can invert the wave's sign; it cannot
learn an arbitrary quadrature rotation or mix another color's wave into it.
Contributions **sum across bins**, replacing the old normalized-wave average
and output-sigma multiplication. Exact zero measured red/blue waves force exact
zero red/blue corrections even when the contextual gates are nonzero. The
inherited local zero-variance routing still returns the anchor exactly.

The 24 context coordinates are the previous 18 green coordinates at 65/33/17px
packed scales, plus six red/blue nominal-power and green-cross coordinates.
Nominal coefficients divide projected sums by the **square root** of supplied
RAW trace variance. Innovation is correlated with the observations, and local
overlapping boxes reuse samples. These values are features, not calibrated
innovation noise or probabilities. The source's shorthand about phase and
variance should be read with the signed-gain and square-root definitions here.

Noise produces nonzero own-color waves even in a truly flat scene. Finite-window
edge leakage, spatial gate modulation, overlapping bins and unresolved aliases
can still create false texture or color. The restrictions above are engineering
identities, not an image-quality or flat-safety result. Additional color
measurements, least-squares units, real bounded gates, mode summation and head
capacity change together; comparison with V197 tests the combined architecture.

## Completed engineering checks

The **23 new CPU tests** compare every wave pixel against independently written
NumPy five-column least squares and interpolation. Known camera-linear waves
verify amplitudes and native phases for all four Bayer layouts in FP32/FP64.
Other checks cover mixed layouts, affine rejection, singular Nyquist rank,
zero-color synthesis, gain bounds, isolated gradients, strict state loading and
mixed/all-ADC routing. A broader wave regression run passes **85 tests**.

Actual trained-anchor admission passes **eight bit-exact initial parities**:
cached mesh, photo, mixed, flat and ADC training batches, plus held-out real sky,
cab and building contexts. Seven noisy cases independently compare CPU/GPU
feature extraction and nonzero readouts. Two training-only mesh/mixed updates
compare all four head gradients to CPU and perform a real model/Adam/EMA/CPU-CUDA
RNG restoration between updates. Those probe weights are never full-training
initializers. Four subsequent strict CPU raw/EMA loads check **772 frozen
anchor tensors** across the two probe checkpoints. Peak admission CUDA allocation
is **6.233 GiB**, not a 100MP performance measurement.

[Source-bound preparation, admission and launch evidence](results/v198-cfa-innovation-prepared-v1.json).

## Full training and required quality comparison

The launched run starts a fresh head with seed `202611080198` and uses the same
1,000 cached rows as V195/V197: **900 noisy updates, 3,600 images and 100 ADC
skips**. The V195 Whole ten-term objective, coherent coefficient 0.50, clean-target
masks, pair units, domain weights, LR schedule, decay and clipping are retained.
Only the four new head tensors train. Row-eight restoration has succeeded and
continues at row nine without repeating the prefix. Five compact checkpoints
bind the frozen anchor rather than copying it.

A registered controller polls the actual worker PID and creation time, then
runs the frozen full-trace/checkpoint CPU audit after that worker terminates.
The private trial root is
`.cache/quality-20261108/V198-cfa-innovation-wave-trial-v1/`; launch records and
status files are authoritative for progress after the public snapshot.

Both raw/EMA endpoints require the full same **822-case** quality design,
including faint/absent mesh, blank areas, actual quiet regions, fresh flat fields,
natural photos and both held-out GFX scenes. Compare at least V195, V197 RAW and
innovation endpoints, and the retained quieter V187 option. Inspect the actual
building artifact as well as cab crossings, sky, foliage and coarse fence.
Include both cab ROIs and noise profiles. Reports need at least two native 100%
noisy/restored/exact-GT triplets per improved model, with identical coordinates,
transforms and pixels, checkpoint hashes, noise conditioning and exposure.
ISO100 AHD and SOOC JPEG views are independent qualitative references, not exact
GT; aperture, exposure time and moving subjects differ.

Both protected capture families, JPEGs and siblings remain outside training.
The total trial budget is **2 GiB new local storage**, with a 40 GiB free-space
floor and no external writes. Existing data are read in place. No new source
images, noise draws, parent/DINO predictions or RAW decodes are generated, and
original photos or unavailable `/mnt/dataz` are not accessed. All previous 104
neural source files are unchanged; the new architecture is the 105th file.
