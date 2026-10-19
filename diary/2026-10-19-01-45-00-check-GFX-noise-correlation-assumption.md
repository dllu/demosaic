# Check cached GFX correlation before changing noise synthesis

Followed up primary AIM 2025 RAW-denoising material while the current full-photo
review runs. It emphasizes synthesis/training and real dark frames; its scores
use a different RAW-to-RAW/ISP protocol. No external data/code/weights imported.

Ran an exploratory stdlib/NumPy probe on all four existing native512 GFX contexts.
The fixed sky's maximum of 66 Haar correlations is .02324, below conditional
Gaussian/PG simulation q95 .02653/.02570 over 128 draws each. HH variance agrees
with the input-only prior within approximately 1–6% across phases. This does not
establish true noise independence or calibration. The textured contexts have
much larger correlations, confounded by scene detail; the sky simulations are
not matched nulls for them. All cases and raw coefficients are retained.

Known planted row/column controls recover .24177/.15146 versus theoretical
.24242/.15254. A separate einsum/corrcoef auditor verifies all 264 real values,
simulation quantiles and control replays, maximum real-value discrepancy
4.44e-16. Both actual executions exit 0 without Torch. Cached input hashes stay
exact; no original RAW decode, training admission or noise/default/model change.

This result gives no evidence to prioritize invented sensor correlations over
the observed detail-recovery failures. The active fixed model comparison and
its original criteria remain unchanged.
[Diagnostic](../docs/gfx-noise-correlation.md) and
[complete evidence](../docs/results/gfx-haar-noise-correlation-v1.json).
