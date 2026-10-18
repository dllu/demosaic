# Audit fresh RAW coordinate learning at 64 updates

Previous goal turn made progress: commit `9f0d12c` implements lower-memory
native RGB16 export, verifies all pixels in six 102MP trials, and was pushed.
This turn verified the exact live training, review, compilation, corrected-grid
and CPU diagnostic owners. DINO passed its retained 32k boundary; no-DINO's40k
endpoint remains complete. No frozen source, model recipe or schedule changed.

The fresh-coordinate CPU diagnostic reached its first predeclared whole-fixture
evaluation at64 updates per arm. It still uses identical fresh weights/initial
bilinear predictions, the same16 actual training observations, and constant
LR2e-4. The remaining128/256 evaluations are pending, with the original yield
policy for owned inference/timing stages. No learned weights are exported.

64-update/initial MSE ratios, balancing batches separately in each domain:

| Arm | Commons/procedural | Native synthetic | Paired measured CFA |
| --- | ---: | ---: | ---: |
| Original RAW | .942247 | .988923 | 1.164589 |
| Gain32 | .931684 | .917611 | 1.261027 |
| Noise companding | .983162 | 1.005559 | 1.151518 |

Neither alternative provides a broad reduction. Gain32 improves native
synthetic MSE more but worsens paired MSE; companding offers no broad fix.
All nine domain/arm loss ratios exceed one. This short, repeated training-set
diagnostic does not establish convergence, generalization, a final ranking,
or how the original long-horizon quality models will perform.

Independent audit retained at
`/mnt/external/demosaic/benchmarks/packed-isotropic-fresh-coordinate-CPU-v1/interim64/`:
the executed `audit.py`, immutable curves through64, complete192-row prefix and
receipt. It rehashes all61 guarded/source/input files, verifies the exact live
owner, mode/update/observation order and finite losses/pre-clip norms, and
recomputes all36 domain means with math.fsum. Maximum reduction difference is
zero. All initial case losses/MSE agree across modes; common model/RNG hashes
and actual original all16 bilinear-output checks remain recorded.

Clipping is frequent:55/64 RAW,64/64 gain32,57/64 companding updates. These
counts are descriptive; no clipping ablation or causal explanation follows.
The diagnostic continues unchanged. The public interim receipt and table are
linked from `docs/packed-isotropic-fresh-coordinates.md`.

Rechecked primary JD3Net and August2026 structural-guidance publications while
waiting for the comparison. Their budgets, losses and data domains differ
from this implementation; they do not justify an unmeasured recipe change.
The existing research notes already cover these methods, so no new algorithm
or availability claim is made from the recheck. SOTA, decisive real-photo
superiority and the100MP/10s target remain unmet/unproven.
