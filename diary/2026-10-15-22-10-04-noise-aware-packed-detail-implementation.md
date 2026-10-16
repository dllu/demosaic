# Noise-aware packed detail implementation

Previous goal turn was progress: source admission, complete V37/V38 and V39
quality reviews, exact comparator reuse and pushed commits. No owned GPU job
was live on revalidation; Commons download continues with512GiB reserve.

Implemented optional packed_detail_prior, defaultfalse for checkpoint parity.
Compute the physical highpass residual MHC−expandedArea2, derive per-color/
output/input-phase noise energies with144 basis impulses, use GaussianWB ratios
or unitWB for Poisson/GAT, and apply a7px local Wiener gain. Zero variance gives
gain1, preserving ADC detail; native phase output/coarse correction remain.
All physical operations stay IEEE FP32;3D nonpersistent buffers permit channels-
last. Correlated RGB noise is not whitened; low-count GAT and boundaries remain
approximations. The physical prior does not use references or fit transforms.

Added phase_lr_multiplier: default1 preserves original optimizer grouping;
otherwise phase_adapter/head get a separate rate under the same warmup/cosine.
Changing it on resume fails before loading optimizer state. Checkpoint model
configuration also prevents changing the prior during resume.

All321 tests pass in26.63s; Ruff passes. Default full/packed behavior matches
SHA-pinned old implementations; Monte Carlo validates each CFA/RGB/output-phase
variance with WB; ADC16-bit ramps, odd packed dimensions and BF16 preserve the
native values. Flat Gaussian noise is attenuated. Both phase modules receive
gradients; channels-last checkpoint output is identical. Optimizer state resume
and LR schedule match in the new grouping. One initial test compared decimal
floating representations strictly; corrected it to numerical tolerance.

Real CLI smoke from verified V34 EMA:6 CUDA updates with genuine DINO, then
resume to8, all domains, finite loss/gradient norms, phase modules updated.
Attempting LR multiplier1 instead of10 is rejected and checkpoint SHA unchanged.
Final group rates2.4e-6/2.4e-5 match the schedule. Receipt under
docs/results/packed-detail-smoke-v1.json. Engineering evidence only; no quality
or speed conclusion. Originals/protected/GFX sources remain outside training.

Prepared V40/V41 configs with priortrue and phaseLR1/10, same initializer,
seed47/B16/baseLR3e-5/planned3000 and original53 native targets as V37/V38.
Stop1000, require all41 logged observations to match V38, then real/full427/
fullGFX quality review with native exactGT triplets and approximate real refs.
This isolates the repair from the V39 data extension. Goal remains active.
