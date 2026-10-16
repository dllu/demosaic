# Packed-resolution restoration prototype

Implemented an isolated experimental `rgb_processing_scale: 2` variant while
the main worktree finishes the V34/V36 geometry evaluation. It retains genuine
frozen DINOv3 and every pretrained RGB CNN tensor, moves the CNN to packed
resolution, supplies all four sensor values and phase labels, and adds a zero
projection plus a12-output phase head. The existing full-resolution MHC path
bypasses the coarse correction. Physical operations/output remain IEEE FP32.

The MHC-plus-area2 marginal noise gain is derived by basis impulses for each
CFA, including WB ratios for Gaussian profiles. Canonical RMS is.6564979553,
not the naive.5. Covariance is not whitened; low-count GAT variance remains
approximate. The changed pretrained input statistics and initially noisy detail
bypass need actual training and qualitative assessment.

The first real CLI smoke failed before training: PyTorch's channels-last model
transfer interpreted a5D physical-kernel buffer as a volume. Flattened its
support into a3D nonpersistent buffer and added channels-last coverage. The
successful six-update CUDA smoke uses the pinned DINO revision and V32-step2000
EMA, sees Commons/native/paired domains, has finite losses and gradient norms,
and updates both new phase modules. It is not a speed or quality benchmark.
Receipt: `docs/results/packed-rgb-smoke.json`; failed/successful directories
retained separately under `/mnt/external/demosaic/benchmarks/`.

Ruff passes. Full292 tests pass in31.41s after the buffer fix. Final15 targeted
tests pass in5.99s after adding two more old-model parity modes. Tests pin the
pre-change source by SHA, compare default outputs bit-for-bit, preserve16-bit
ramps under BF16 for all CFAs/odd packed sizes, check individual phase routing,
compare noise energy with Monte Carlo for all CFAs, verify gradients and an
identical channels-last checkpoint roundtrip. Default parameters/behavior stay
compatible with existing checkpoints.

Queued controller PID567918 in this worktree waits for main full-review
PID443420; no competing owned GPU training is started. It requires the full
V34 photo mean to improve over its matched V32 first1k control, then measures
scale1/scale2 in batch16 ABBA order and a separate8/32/64 packed sweep. Quality
V37/V38 keeps batch16, same V34-step1000 EMA, fresh AdamW/EMA, seed47, complete4x
corpora, per-step RNG, LR3e-5/planned3000 and stops after1000. All logged batch
hashes must match. Subsequent standard evaluators include full427/native GT
triplets and fullGFX foliage/fence with both RawNIND calibrations. No training
or quality result is assumed at setup. Source imports remain in this isolated
worktree even after merging its commit.

The goal remains active: no decisive qualitative SOTA result or10s/100MP result.
