# Coarse trial and matched joint tuning

Implemented an optional pooled RGB correction, factor8/width24/four blocks for
V17,27,696 parameters. A zero head preserves initialization, and zero sensor
variance guarantees zero correction. Pooled input variance is a scale proxy,
not posterior covariance. Arbitrary even sensor dimensions are padded/cropped
correctly. New tests verify warm identity, ADC-only preservation, gradients only
in the selected branch, exact CPU resume/frozen weights, and representable broad
error removal while preserving a checkerboard in the pooling nullspace.

Refactored the original RGB correction without changing existing checkpoint
outputs: actual archived V15 code versus current code gives zero differing
values across two512×512×3 CUDA outputs (1,572,864 values). Sources and exact
weight hashes archived under evaluation/coarse-backcompat-20261015.

V17 first1000 steps from frozen V16 step5000, original losses/data mix, do not
meaningfully improve quality: known/unseen measured PSNR53.26982/53.08522 versus
parent53.27466/53.07857. Same64-photo synthetic screen31.96726/.924065 versus
31.96724/.924058; flat32/64-pixel errors do not improve. Held at review and not
promoted. Optional module remains disabled in current V16/README candidate.

Started V18 joint restoration/fine-refiner tuning and V19 refiner-only control
from identical V16 EMA bytes, identical architecture, seed43, LR3e-5 and5000-step
schedule, review at1000. DINO backbone remains frozen and coarse correction off.
Added optional actual-batch SHA256 tracing at logged steps; strides/dict order
do not matter, all tensor types/shapes/data do. Initial sampled hashes match.
At step1000, all41 sampled batch hashes and CPU/Python/CUDA checkpoint RNG states
match. Joint/control known measured PSNR53.17999/53.28990, unseen53.08643/53.07817:
joint tuning does not improve real aggregate quality at this review. It improves
the64-photo synthetic screen31.99174/.925095 versus31.97042/.924121. Neither is
promoted. Both resumed the original5000-step schedule to assess convergence;
immutable1000-step weights and crop reports retained. Protected scenes and GFX
qualitative photo/siblings never enter these training splits.160 tests pass.
