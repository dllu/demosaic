# Genuine ConvNeXt pyramid passed CUDA engineering validation

After publishing the completed original10k manual review and confirming owner
exit, ran the complete suite in frozen candidate checkout797cfc8:496 passed in
87.25s. Ran `scripts/preflight_dino_pyramid_cuda.py` with that completed review's
SHA pinned. Actual preflight exited successfully; its full private receipt is
under `/mnt/external/demosaic/benchmarks/dino-convnext-pyramid-cuda-v1/`.

Published `docs/results/dino-convnext-pyramid-cuda-v1.json`. Genuine frozen
features, mixed-precision initialization equality, batch16/native256 two
discarded Commons updates, gradient flow, frozen encoder, portable EMA and
exact complete-state restoration before a third native update all verify.
Peak allocation7.14/7.91GB includes original/restored models. No isolated speed
or trained-quality result follows; bitwise uninterrupted CUDA optimization is
not asserted.

Prepared a source/config/input/weight/review-pinned first1000 controller that
will compare against all three immutable original fresh first1000 checkpoints,
using the original planned10000 LR schedule and matching all41 logged batches.
It requires this successful CUDA receipt before creating its own run and
evaluates paired/full427/analytic/fullGFX/three additional cached cameras.
Manual native review remains separate from its automated completion status.
