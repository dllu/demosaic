# Queue corrected-grid CUDA and full-frame validation

No-DINO finishes the original40k review boundary, checkpoint SHA
5708fdc19542ca1ef1aaafec25038dc049e4f5027782809846cf6d888ebed2cc.
The controller records finite model/EMA/852 Adam states and1602 training rows.
DINO resumes its own8k raw model/EMA/863 Adam/global RNG state before updates;
its actual restoration receipt verifies those hooks. All first16 actual resumed
DINO observation fingerprints match no-DINO exactly. The original160k horizon,
data, LR/precision and frozen physical source50dc remain unchanged.

Added scripts/evaluate_packed_grid.py and scripts/review_packed_grid.py.
The first compares legacy/corrected tiling and a whole-context forward on two
existing native510 CPU photographic observations. It saves full F32 outputs,
syntheticGT metrics and native triplets without changing any model tensors,
keys or IDs. The second independently replays those arrays/metrics on CPU,
checks every corrected F32-to-RGB16 export pixel, compares every legacy/new
RGB16 channel value with signed subtraction and generates before/after native
GFX views using the same decoded16-bit representation and display transform.
Legacy40k exports are reused, not rerun. RGB16 differences are not unquantized
F32 equivalence or real-GT scores. Metric replay absolute tolerance1e-4 is
predeclared for CPU reduction order, not model-quality acceptance.

The standard GFX crops lie outside the changed final tile row/column. Added
two geometry/input/reference-only ROIs before any corrected full-frame output:
right-edge building beams/windows[11300,3600,160,160] and bottom-edge deep
shadow[7200,8400,160,160]. Both preserve full512px noisy contexts. The new
configs/gfx-qualitative-grid-edges.json is supplementary; standing foliage,
fence, building and sky remain. Decoding only the locally cached ISO100 RAF
with the existing own-CFA LibRaw AHD calibration reproduces all four old
reference crops bitwise, then saves the two additional references/contexts.
No source hard drive is accessed, no original is modified, and none of the
GFX scene/siblings enters training. ISO100 references remain labeled not GT.

Fixture v2 SHA d2928cb74103067260ed9ce251f37f47c254d2e5f43d04eb56080b64104ae537.
Actual no-DINO40k and retained genuine DINO8k CPU preflights pass on it; the
DINO's six arrays reproduce its earlier fixture bitwise. The final frozen
no-DINO40k executable's six arrays match root execution bitwise. I inspected
and published its two native noisy/denoised/exactGT triplets; noise and soft
detail remain. These CPU selected views do not establish a general quality gain.
A separate existing8k102MP RGB16 identity check covers all305987556 values,
including the final partial chunk, without new inference.22 focused tests pass
in2.39s, covering16-bit overflow, chunk/pixel counts, wrong/ambiguous controls,
whole-F32 differences and original quarter-review gates. Ruff checks pass.

Launched only a CPU sleeping controller, PID1949709/create-time1792280689.52,
after exact compilation owner1892187/create-time1792277635.47. It verifies the
successful original40k training/full review and independent state provenance,
then waits for compilation's actual owner and last child to exit. An unrelated
compiler rejection/failure does not turn this separate eager-only validation
into a compiler retry. Failed required quality/integrity checks stop it before
GPU use. Guarded inputs are rechecked. No training, compilation, protected-final
scoring, automatic promotion or continuation is added.

Plan SHA d597a535a36bd6b72e31d7b44677bf3683fae9a88e6dd29d3ad2c0205ed52a16;
controller SHA e0d3bfaa78b303560d2a5f27852057eff26ccd22006aeb55f35a5ad7b69a8a77.
All161 guards/29 inputs match. The queued protocol makes two CUDA photo
comparisons plus two fresh eager full102MP cases, each one excluded full warmup
and three timed restores. It creates12 syntheticGT and24 GFX native triplets,
including both affected edges. Manual inspection and actual speed/quality
assessment remain after execution. Its v1 preparation was never launched and
is marked superseded; v2 adds the necessary affected-edge coverage.

Live status: /mnt/external/demosaic/runs/packed-isotropic-corrected-grid-workflow-v2.json.
Private source/plan: /mnt/external/demosaic/benchmarks/packed-isotropic-corrected-grid-workflow-v2/.
Public note: docs/packed-isotropic-corrected-grid-queue.md.
Public receipt: docs/results/packed-isotropic-corrected-grid-queue-v2.json,
SHA2e2a6f274763ac68087cf3a18459f91901c8369e5f35375f3200340669aa1ecf.

The working V43/README remain unchanged. The full SOTA/real-superiority/speed
objective is incomplete; no corrected-grid CUDA result is claimed by a queue.

At2026-10-17T16:51:10.512656-07:00, DINO is at step15725; no-DINO is complete at40000.
