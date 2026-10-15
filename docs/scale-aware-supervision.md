# Scale-aware measured-CFA supervision

The V17 and V24/V25 reviews found little reduction of 32/64-pixel residual
error, despite extra correction capacity and context. V26/V27 test a different
hypothesis: the original objective gives insufficient pressure to reduce these
small absolute errors. This is a controlled training experiment; V16 remains
the reviewed model until quality evidence justifies promotion.

Both arms start from frozen V16 step5000 and append the same factor 8 pooled
RGB correction used in V17, with 27,696 trainable parameters. The restoration
body, genuine pinned DINOv3 backbone and fine correction remain frozen. Both
use seed 46, LR 5e-4, the original 50/50 paired-RAW/Commons recipe, unchanged
augmentation and noise distributions, a planned 5000-step schedule and a
predeclared first review at 1000 steps. Per-step data RNG and sampled batch
hashes verify matched observations. Native-target substitution is disabled.
Protected final and personal GFX scenes/siblings remain excluded from training.

V26 adds `multiscale_sensor_weight: 0.01`; V27 uses 0. The new term samples the
RGB prediction at its actual CFA phases, then compares non-overlapping 4×4,
16×16 and 32×32 blocks in packed phase coordinates (sensor footprints 8/32/64).
For each fully valid phase block:

`standardized error = sum(prediction − reference) / sqrt(sum(input variance))`.

The variance is `shot * clean_reference + read` in observation sensor units.
The clean reference avoids conditioning weights on positive noisy tails. The
sum uses an independent-input-noise proxy, **not posterior RGB covariance**.
A Charbonnier penalty in these noise units is averaged within each scale,
then equally across the scales. Incomplete reference blocks and ADC-only
observations contribute zero. Synthetic masks exclude clipped/reconstructed
highlights and out-of-range targets. Real masks come from measured clean CFA
samples, with no new AHD fine-detail supervision. Independent reference noise
and imperfect registration remain limitations of real pairs.

The term penalizes coherent block-mean error more strongly than phasewise
zero-mean fine error. Existing linear/rendered/gradient/highlight/sensor losses
still apply. No inference input, output, transform or arithmetic changes. The
loss weight is opt-in, defaults to zero, is checked for finite nonnegative
values, and cannot change on exact resume. Existing default-loss behavior is
preserved. Physical loss operations use IEEE FP32 even inside BF16 training.

Validation before training: all 196 tests passed in 10.58 s and Ruff passed.
New tests check analytic noise scaling under all four CFAs on CPU/CUDA,
fine-error nullspace, measured-only targets without AHD dependency, invalid/
clipped/ADC-only exclusion and zero gradients, default compatibility, weighted
integration into both objectives, and exact coarse-only resume with the new
term. Genuine-DINO startup outputs match V16 bit for bit over 6,291,456 RGB
values across four CFAs and ADC/noisy inputs.
[Source, parent and startup identity receipts](results/scale-loss-v26-v27-startup.json).

Configs: `configs/dino-scale-loss-v26.yaml` and
`configs/dino-scale-control-v27.yaml`. Both run directories are under
`/mnt/external/demosaic/runs/`. Each archives actual source and data identities.
The startup logs show matching sampled batches and larger coarse-branch
gradients with the new term; that demonstrates optimization pressure, not a
quality gain. The 1000-step review must include both real development panels,
the matched synthetic screen, residual-scale diagnostics, at least two native
triplets per candidate and the new GFX pair's fixed texture regions.
