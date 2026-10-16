# Corpus first gate regresses; correct the fresh DINO precision control

V50 completes1000 updates/full review with22 shared paired/native logs exact,
17 changed Commons batches and two unchanged Commons batches. Known primary
falls.01737dB, full-photo PSNR.05864dB, with negative source-bootstrap intervals.
Unseen/procedural means also fall but their intervals include zero. Stop this
checkpoint; preserve the larger corpus for future converged trials. No claim
that more data is generally harmful. Twenty native comparisons and two complete
RGB16 files verify; no decisive visual gain and persistent soft fabric/foliage/
fence. Full GFX took33.47s, not a repeated timing benchmark or10-second result.
V43/README aliases remain fixed.

Constructed the genuine larger frozen DINO-B and compared fresh Gaussian
initializers with S/no-context. All66 shared tensors match the established
c7ebf6... initializer hash. The first CPUFP32-only comparison passes, but
inspection finds a material AMP confound before training: a zero DINO offset
promotes the middle skip toFP32, while no-context keepsBF16. Genuine CPU32px
outputs are exact inFP32 and differ up to.00114676 underBF16. This does not
invalidate V47/V49/V50, which all use DINO and identical arithmetic.

Added optional `rgb_middle_skip_fp32`, defaultfalse with no new tensors or
parameters. All three previously untrained fresh recipes enable it, matching
the original DINO arithmetic while preserving legacy defaults/current model
behavior. Six targeted tests include exact BF16 absent/zero-offset values and
input/weight gradients, legacy defaults, unchanged FP32-offset behavior and
portable checkpoint policy. The complete CUDA suite passes379 tests in40.18s.

Corrected CPUv2 checks12 all-CFA/noise/shape/FP32/BF16 combinations with no CUDA
initialization. Genuine CUDA checks pass all three initializers inFP32/BF16/
FP16 at three priors/four CFAs, plus two actualB16/native256 AdamW updates per
arm, finite/context gradients, unchanged original foundation hashes and exact
portable predictions. Peak allocation6.38–6.74GB is fixture evidence, not a
throughput comparison. Source/config/weights/driver snapshots are archived.

The next actual training is a fresh no-context/S/B comparison from the verified
Gaussian prior, with zero measurement/gates, seed48/B16/LR1e-4/planned10000 and
first1000 review. Use the fixed original40170 Commons/native128/paired32 corpus
to isolate architecture, independently of V50. Require all41 logged observations
exact across arms. Recompute both RawNIND calibration variants with the complete
paired/photo/procedural/GFX review; include at least two native exact-GT crops
per neural checkpoint and verify all ten fullRGB16 outputs. One early seed/gate
does not establish convergence, current DINO benefit or SOTA.
