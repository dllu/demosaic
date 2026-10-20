# Check stabilized noise before another architecture change

Previous goal turn: progress. It committed direct physical-anchor construction,
116 passing tests/one CUDA-only skip, genuine V63 CPU output/89 parameter-gradient
byte parity, a deferred CUDA check and the retained spectral1k state/RNG audit.
This turn began03:52UTC. Exact controller620536/1792466470.15 and
spectral child628726/1792467113.42 were confirmed live atstep1,275; all exact
review/closure/reference/native-package and both implementation probes were live
and waiting. No trainer was restarted or interrupted.

Reviewed the primary July31 v3 PixIE paper and the author's publication page.
The [research note](../docs/research-pixie-followup.md) records semantic routing
as a future hypothesis, without a RAW reproduction or released-artifact claim.
Our ConvNeXt projected fields already use continuous bilinear interpolation;
that alone is not an identified missing feature. No new architecture/recipe
was launched alongside the current comparison.

Checked a concrete physical assumption instead: stochastic CFA profiles provide
unit-variance proxies before demosaicing, although GAT is approximate and MHC
changes covariance. A new standalone CPU diagnostic computes centered GAT
moments over24 mean/read combinations with128/256-node quadrature, an analytic
normal positive-part second moment, counts0–320 and±12 Gaussian sigmas. All24
agree with262,144 independent samples per case within the declared six-SE
checks. The production expectation tables also agree at checked means.

Interior MHC impulse coefficients preserve constants and their12 diagonal
variances agree with analytic stencil-energy fractions for all four CFAs.
Unit independent CFA noise gives mean RGB/phase variance11/12; RGGB within-cell
covariance eigenvalues range.02285884–3.28472562, with strong cross-color/spatial
correlation. Each four-CFA covariance check uses32,768 independent Gaussian
fields; the largest element error is3.134 estimated SE.

Two complete unclipped/unquantized Poisson-Gaussian GAT→MHC flat checks use
32,768 fields each, shot.00256/read variance.0000262144. At gray.01/λ3.90625,
GAT variance1.05792645 yields mean RGB/phase variance.96976591. At gray.18/
λ70.3125, corresponding values are1.00038867/.91702295. Both full empirical
covariance matrices pass their fixed checks. These are flat moments, not carrier
response or learned outputs. The dark mean is close to1 and other regimes have
both signs of deviation; this does not justify a large global prior reduction.
Exact marginal variance also cannot whiten the correlation. No quality cause
or camera-specific calibration is established. ADC, saturation and reflected
boundary statistics are outside this study; the zero-stochastic-noise path is
not directly described by the unit-proxy approximation.

The final plot fixes only nonnegative axes/legend placement and was actually
viewed. All24 rows and12 saved coefficient/covariance arrays replay byte-exact
between v1/v2. A scratch byte-view observer rejected Fortran-strided coefficient
arrays; canonical C-order byte comparison fixes that observer. Reconstructed
the first executed driver by reversing the plot edit and required its exact
original SHA; both driver versions and matching frozen physics sources are
archived. A reproducible source/replay reader verifies those hashes and AST
identity of active-training GAT/expectations/noise/normalization, plus full CFA
module byte identity. Torch CPU RNG stays exact; CUDA was never initialized.

Final receiptSHAc11986d861e6b8a71ebb754bb92352fa5bbdf2de2df9427ec6b39c6f5b3971f5;
source/replay auditSHAb38190a7d3e4c93a9536cb4251bad1d7ab61727eca89c24635176c808b13e62d.
Ruff lint/format and diff checks pass. This is generated-field diagnostics,
without photographs, learned-model evaluation or new noise-conditioning defaults.

Confirmed requirements/research documents are not bound to any active queue
before updating them. Corrected the stale84,867 active-corpus row to88,508
training/2,303 val/2,255 test, while preserving the older frozen cohort's scope.
Added current completion/audit and implementation-cleanup evidence pointers.
The source protocols, data manifests, active model and all quality gates stay
unchanged.

At04:09:44UTC the same exact spectral child was live atstep2,350 with.958s/update,
all110 recorded source/forward/loss dictionaries matching control. All quality/
native-package and deferred-probe owners were live and waiting, RAM58.3GiB
available/external535.2GiB free. Original photographs and spinning disks remain
untouched. Full spectral4k and the complete actual native/numerical review are
outstanding; PROMPT goal stays active, without SOTA/native-superiority/10s claims.

[Diagnostic and plot](../docs/stabilized-noise-proxy.md),
[complete receipt](../docs/results/stabilized-noise-proxy-CPU-v2.json),
[individual moments](../docs/results/stabilized-noise-proxy-moments-v2.json),
[source/replay audit](../docs/results/stabilized-noise-proxy-source-replay-v2.json).
