# Batch4 versus batch16 at equal example counts

The [completed CUDA diagnostic](results/packed-isotropic-batch-learning-CUDA-v1.json)
finds modest batch16 benefits with scaled residuals at equal example counts.
Final Commons/native MSE is1.4%/4.0% lower than scaled batch4; paired MSE is
nearly unchanged. This motivates a full-data mixed-batch trial, without proving
photographic quality, convergence or a production batch choice. The
[original launch plan](results/packed-isotropic-batch-learning-CUDA-launch-v1.json)
remains unchanged. The earlier throughput sweep favored batch4 on its own recipe.

Four fresh seed51 models form a two-by-two comparison: original RAW versus
input gain32 with residual÷32, each at batch4 and batch16. Initial parameters,
capacity and physical bilinear predictions match. The preceding
[local-contrast test](packed-isotropic-local-contrast.md) is complete; its
filters are not used here.

Every arm consumes the same ordered4096 example draws from the16 frozen
training-only B4 fixtures, with identical noise. Each round takes four successive
fixture groups. Batch4 makes four optimizer updates. Batch16 joins their
physical inputs in one forward and averages the four unchanged domain losses
before one update. This preserves original per-group paired-mask/highlight
reductions and the original domain proportions. It is a real16-example forward,
without batch-statistical normalization or cross-example conditioning.

The fixed recipe is AdamW LR2e−4/decay.01 and clipping1, CUDA IEEE FP32 NCHW,
no AMP/TF32. After256 rounds, batch4 has1024 updates and batch16 has256.
Per-update LR/decay stay fixed, so cumulative updates/decay differ. This compares
equal-example behavior for this recipe; it is not a search for batch16's best
LR or a throughput measurement. Evaluation at1024/2048/4096 example draws uses
all16 training fixtures and retains each arm's optimizer update count.

## Completed4096-example result

Each cell is **original-domain loss / MSE** divided by the common initial
full-fixture value. Lower is better. All are errors on the repeated training set.

| Arm | Commons/procedural | Native-clean | Paired measured CFA |
| --- | --- | --- | --- |
| RAW, B4 | .96982 / .77251 | 1.07426 / .99794 | 1.08432 / 1.04063 |
| RAW, B16 | .97280 / .81726 | 1.07104 / .99060 | 1.24112 / 1.04710 |
| Gain32 + residual÷32, B4 | .90274 / .74728 | .96677 / .98862 | .99206 / .99911 |
| Gain32 + residual÷32, B16 | .89912 / .73664 | .96850 / .94912 | .98869 / .99962 |

Batch16 alone gives mixed results. With scaled residuals, it improves final
Commons loss/MSE, native MSE and paired loss over B4, while native loss is
slightly worse and paired MSE differs by only.05%. Neither paired arm shows a
meaningful MSE reduction from initialization. The midpoint also favored B4 on
Commons, so a short intermediate curve would have given a different ranking.
This is one seed and64 fixed observations, without a held-out quality estimate.

The successful B16 probe joins four originally scheduled B4 groups, which can
have different domains. The [subsequent production implementation and execution
sweep](mixed-optimizer-batches.md) preserve those indices, per-group losses and
degradation RNG. B4 gradient accumulation is fastest for the same effective16.
This learning probe itself supplies no throughput evidence, and no ordinary
single-domain B16 recipe is switched on its strength.

Four focused tests verify actual batch16 losses and nonzero trunk/head gradients
against four accumulated batch4 calculations across synthetic/native/paired
domains and all CFAs, exact single-group loss equivalence, unchanged inputs/state
and rejected empty/unequal groups. Ruff passes. Original domain supervision and
paired-reference limitations remain unchanged.

Independent audit verifies2560 ordered finite training records and96 domain
means, all40 inputs/46 guards, and4096 identically ordered example draws per arm:
1792 Commons/procedural,1024 native and1280 paired. All852 Adam states per arm
are finite at the expected1024/256 updates, fixture fingerprints remain
unchanged, and the exact GPU owner exited.

All learned weights were discarded. There is no GFX/validation/protected-final
optimization, source admission, EMA, pretrained initialization, production
promotion or automatic restart. The separate CPU coordinate diagnosis is also
complete. Both studies retain their original frozen protocols.
