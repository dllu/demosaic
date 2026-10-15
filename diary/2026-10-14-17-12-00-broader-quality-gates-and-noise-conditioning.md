# Broader quality gates and noise conditioning

The previous goal turn made concrete progress: implementation, trained models,
verified DINO weights, native RAW runs and pushed commits. Revalidated all three
live jobs from process state before proceeding. Training and preparation remained
healthy, with substantial available system memory.

Added a paired quality suite across four CFAs and seven noise/exposure cases,
native crops, float32 SSIM, linear/rendered PSNR, chroma/gradient and masked
highlight/shadow errors. It freezes checkpoint bytes and preserves source and
model provenance. Per-image noise streams are stable across model/batch order;
paired bootstrap comparisons resample sources. Tests cover the numerical metrics,
pairing and correct handling of absent highlight/shadow regions.

The early 8-photo/2-synthetic diagnostic exposed a material weakness hidden by
the original single condition: RawNIND is stronger on shadow PSNR/SSIM and on
high-noise SSIM. For example, RGGB shadows scored about 33.31 dB / 0.805 SSIM for
DINO step 10500 versus RawNIND 35.01 / 0.896. Noiseless/ordinary conditions favor
our model, but this is not the requested broad qualitative superiority. DINO and
control snapshots here also have unequal training steps, so do not interpret
their small difference as an ablation result.

Added bounded-memory flat-patch noise estimation with Haar details, detrended
texture rejection, nonnegative regression and uncertainty/failure reporting.
Synthetic recovery and insufficient-intensity-span tests pass. Real fits support
the GFX50R/Sony shot priors; Q2 shot is about twice the nominal prior. These are
statistical single-scene estimates, not measured camera calibration. Inference
can consume a reliable profile, with camera/ISO checks.

Added protected-split near-duplicate screening. The 8192-source audit found zero
matches at its declared thresholds; no split memberships changed. Crops and
other viewpoints can evade this screen, so scene separation is not proven.

Research checks: the August 2026 SG-for-JDD repository returns 404. Samsung's
unified-demosaicing code/models declare CC BY-NC-SA 4.0, so they were not adopted
into this commercially usable project. The lack of these comparison weights is
not a global blocker; quality work continues.

To address weak noise adaptation, implemented optional spatial scale/shift
conditioning at every encoder/decoder scale and the bottleneck, using normalized
log variance. It starts as the exact existing function, preserving warm-start
weights, with nonzero conditioning gradients verified. This follows the deep
condition-modulation direction discussed in the recent JDD research. It has not
yet demonstrated trained quality improvement and is not enabled for old models.
Current matched 20k runs must finish before selecting their next initialization.
