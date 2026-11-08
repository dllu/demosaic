# Balanced directional pair-response pressure (V195 preparation)

The new training-only loss passes **26 CPU contracts and native derivative checks on20 saved training batches**. No new model has been trained yet. The [V194 saved-output diagnostic](mesh-directional-response.md) found that a high whole-pattern score can coexist with poor response in one crossing direction. This motivates testing more balanced pressure while retaining every existing flat and reconstruction penalty. V187 remains the preferred experimental wave model; V120 Small remains the general recommendation.

For each training pair, remove each channel's spatial mean from the actual target difference. Split its native Fourier coefficients into four angular regions, then repeat with boundaries offset22.5degrees. The two tilings reuse the same target; they are not independent evidence. Each non-DC bin belongs to one region per tiling, with conjugate pairs kept together. Cartesian comparisons make axis/diagonal boundaries exact; Nyquist-axis orientations follow a declared discrete conjugate-pair convention.

For region component `t_s`, compute:

```text
r_s = mean(pair_error × t_s) / (mean(t_s²) + (1 / 65535)²)
loss = mean_over_pairs_and_regions(sqrt(1 + r_s²) − 1)
```

FP64 orthonormal Fourier reductions equal the spatial projections. The positive1DN16 floor limits sensitivity as a component vanishes; there is no hard amplitude cutoff. Averaging the regional losses reduces dominance by a large-energy direction. It does not guarantee recovery where the current readout lacks useful measurements or capacity. Targets and pair labels enter only after inference; no inference gate, reference-conditioned feature or model source changes.

The prospective matched comparison adds weight0.25 per domain to the unchanged nine-term objective:

| Arm | Existing whole-response weight | Additional pressure |
| --- | ---: | --- |
| Whole control | 0.25 | 0.25 × existing whole-response loss, giving total0.50 |
| Directional | 0.25 | 0.25 × mean response loss in eight regions |

Both wrappers preserve all nine original scalar terms, their masks and their FP32 accumulation exactly. Equal nominal added weights do not mean equal gradient norms. The intended model comparison retrains the same508-parameter V187 head from one shared completed V187 EMA state, with identical fresh head Adam/EMA clocks, cached data, schedule and update budget. All189 inherited tensors and all103 neural source files stay fixed. That is a new matched optimization stage, not a claim of uninterrupted prior Adam history. GPU/head admission and a final training/allocation plan remain required.

An analytically missing6DN16 wave beside a correctly restored30DN16 wave receives a stronger recovery gradient under the regional term than under the whole projection. Explicit dense Fourier-basis/spatial derivatives verify arbitrary outputs in both floating-point types and at three floors. Other contracts cover pair symmetry, constant errors, shifts, D4 transport of non-boundary carriers, exact axis/diagonal ties, conjugate-closed odd/even grids, connected empty-pair zero and both wrappers' unchanged nine terms.

**This response term does not punish every false pattern.** Exactly unchanged target pairs give zero loss and gradient, even for an erroneous textured output; orthogonal errors can also be invisible. The existing absolute, pair-difference/common, local/DC, flat-anchor and flat-spatial losses remain essential. Actual quiet/absent/standalone-flat tests and protected GFX crops are required before claiming an improvement.

The native check reuses all20 audited saved V182 RGB batches: four each from mesh, weak texture, photograph, mixed and flat domains;12 batches have paired targets. A separate NumPy calculation constructs real inverse-FFT subtemplates and evaluates spatial inner products and analytic derivatives. All53,477,376 output-gradient coordinates pass, with maximum FP32 gradient difference9.10e−13 and relative L2 difference1.02e−12. Neural Module forwards are forbidden during replay; CPU RNG remains unchanged, CUDA stays uninitialized, and no optimizer, checkpoint load, new source/noise draw, RAW decode or protected input occurs.

The first26-contract suite adds one exact-boundary test to an earlier25-contract pass; both logs and the earlier algebra implementation remain preserved. One unsealed preparation stopped at an inherited disk guard, and another caught an incorrect baseline plan filename introduced while adapting the wrapper. Both stopped before native calculations; their sources and correction receipts are retained. The successful native computation completed once. This CPU-only stage uses a prospective32GiB local/RAM reserve and0.005GiB small-receipt budget after local free space fell to35GiB; older model-trial plans remain byte-preserved.

[Loss implementation](../scripts/directional_pair_objective.py) · [Independent native reference](../scripts/directional_pair_reference.py) · [CPU evidence](results/v195-directional-response-CPU-preparation-v1.json). Both protected GFX families, JPEGs and siblings remain excluded from training. ISO100/AHD/JPEG references remain qualitative, not exact GT. No learned-quality or flat-safety gain is claimed at this stage.
