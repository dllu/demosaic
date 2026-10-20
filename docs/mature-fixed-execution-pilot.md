# Fixed-backend mature precision pilot

**Prepared but not launched.** Quality-first V43/corpus work takes priority at
the user's request. This preparation supplies no new GPU, quality or speed result.

The original full-quality qualification stopped on its matching-policy CUDA
parity limit. A subsequent unchanged original-worker replay also fails that
limit on V43/GFX, so the new evaluation wrapper is not the sole cause. The
failed freezes and all unfavorable outputs remain separate evidence. No
limit is retrospectively changed, and the cause is not isolated.

PyTorch documents that convolution benchmarking can choose different
algorithms across processes, and that different attention backends can give
different low-precision numerical results. See the official
[reproducibility notes](https://docs.pytorch.org/docs/2.14/notes/randomness.html#cuda-convolution-benchmarking)
and [FP16 reduction notes](https://docs.pytorch.org/docs/2.14/notes/cuda.html#reduced-precision-reduction-in-fp16-gemms).
This motivates a new explicit execution intervention; it does not establish
which backend caused the earlier mismatch. Installed runtime at preparation
is PyTorch2.14.1+cu130/CUDA13.0/cuDNN92400.

Freeze `mature-fixed-backends-v1` before new outputs: disable cuDNN search,
require deterministic cuDNN and strict deterministic algorithms, set IEEE
FP32 convolution/matmul, disable FP16/BF16 reduced-precision GEMM reduction
and FP16 accumulation, force math SDPA with full-precision reduction, and
supply `CUBLAS_WORKSPACE_CONFIG=:4096:8` before process startup. Record the
actual settings and restore them exactly after the worker exits its scope.
No model/config/weight/default or training changes accompany this research
policy. Earlier autotuned FP16 ratios cannot be assigned to this policy.

Run two fresh processes serially, each using both original V43/V63 checkpoint
snapshots and all29 frozen pilot fixtures: four standing native512 GFX
contexts, two fixed exact-GT photos, the complete original96 unique analytic
observations, and all-CFA native ramps/one-DN probes. Keep all three precision
policies and the original dtype hooks, policy order, three warmups and four
balanced resident timing samples. Each process runs212 actual forwards,
including188 instrumented and24 timing calls, saving174 captures and24 timed
outputs. CPU engineering proof and physical implementation remain bound to
the original genuine76-forward and subsequent102-forward receipts. The new
focused settings tests are CPU-only backend-contract checks, not GPU evidence.

The first process's FP32 arrays must retain the old FP32 output's1DN16 maximum
and.25DN16 RMS per observation on every fixture. Every capture across the two
new fixed-policy processes must be SHA256-identical, and every same-process
timed output must be SHA256-identical to its own first capture. Save every
array before comparison; failures stop continuation and remain preserved.
Report differences against historical half outputs as diagnostic differences,
without representing them as matching execution policies. This new study
does not turn the original failed half-policy parity gate into a pass.

The first replica supplies a separate finite quality/native review using the
unchanged original photo/analytic/flat/ramp limits. Render all36 native160px
triplets/48 cells from both exact-GT photos and four GFX regions; all settings
and pixels match across methods. Inspect every cell before quality or timing
interpretation, then independently audit the saved F32 arrays and scalars.
ISO100 DSCF3880 remains an independent qualitative reference, not GT.

Require48GiB available RAM stable60s,24GiB active headroom, root64GiB and
external500GiB reserves, and a16GiB worker CUDA cap. Bound each replica to900s
and resource waiting to1h; stop only an exact owned child. No automatic retry,
training, new whole-photo run, export, production/default change, or automatic
full-quality continuation. Estimated local outputs are under2GiB. Even a
finite pass requires a separately frozen full-quality study retaining all
427 photos, known/unseen, analytic/color grids,132 native cells and the
prospective limits already recorded in the full-quality protocol; an actual
100MP16-bit study follows only after full qualification.
