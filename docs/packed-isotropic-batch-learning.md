# Batch4 versus batch16 at equal example counts

The [frozen CUDA diagnostic](results/packed-isotropic-batch-learning-CUDA-launch-v1.json)
is running. This tests optimization behavior after the throughput sweep favored
batch4. No final result, production change or trained model is claimed.

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

Four focused tests verify actual batch16 losses and nonzero trunk/head gradients
against four accumulated batch4 calculations across synthetic/native/paired
domains and all CFAs, exact single-group loss equivalence, unchanged inputs/state
and rejected empty/unequal groups. Ruff passes. Original domain supervision and
paired-reference limitations remain unchanged.

All learned weights will be discarded. There is no GFX/validation/protected-final
optimization, source admission, EMA, pretrained initialization, production
promotion or automatic restart. The separate CPU coordinate diagnosis continues.
The run guards40 inputs and46 frozen files and starts only after the preceding
owned GPU workflows have completed and exited.
