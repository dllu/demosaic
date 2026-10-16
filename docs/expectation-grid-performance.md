# Reuse the invariant Poisson integration grid

Each fresh shot/read profile previously rebuilt an identical2721×321 Poisson
probability matrix and the quadrature nodes. Only the conditional Gaussian
expectation changes with read noise. A single read-only6.69MiB grid now supplies
all profiles; the original operations and reduction order are retained.

All132 tested profiles produce **bitwise-identical** expected values and mean
grids: read noise0..6e− in129 steps, plus16,1000 and1e8e−. The independent dense
integration, Gaussian-limit, sub16-bit round-trip and gradient tests still pass.
Repeated model construction/checkpoint behavior is unchanged. V30's real and
synthetic overall metrics reproduce within1e−7 in the V31 review after caching.

CPU fresh-profile construction,64 uncached profiles/repeat, three repeats:
**5.275→.806ms/profile**, about6.55× faster. This measures table construction;
it is not a6.55× training claim.

The controlled full-training comparison alternates original/cached/cached/
original implementations at batch16. Both frozen code snapshots differ only
in `vst.py`; initializer, actual8× data, worker counts, noise/domain schedule,
DINO, optimizer, losses and EMA match. Each case excludes15 warmup steps and
measures45 real mixed-domain steps. The two-worker Commons4× preparation stays
active throughout, and this remains a shared-machine measurement.

| Batch16 implementation | Mean images/s | Two-run range | Peak CUDA GB |
| --- | ---: | ---: | ---: |
| Original | 26.18 | 25.98–26.38 | 6.94 |
| Shared invariant grid | **29.07** | **28.78–29.37** | **6.94** |

That is an additional **11.05%** measured throughput gain at the same batch
size and CUDA allocation. The ranges describe two runs, not confidence intervals.
Code-file comparison verifies `vst.py` as the only differing implementation file.
The new lower-LR trials use this optimization; the already-running V31 trainer
retained its originally imported implementation.

Full validation after the native4 extension and manifest freezer:
**256 tests passed in37.87s**. Ruff passed and the rebuilt wheel was checked for
exact VST/native-loader/trainer source and all four upstream license notices.

[Complete CPU and training measurements](results/expectation-grid-performance.json).
This optimization changes neither learned parameters nor the noise model.
