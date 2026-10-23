# V102 quality baseline after completed V102/V103 comparison

Recorded: 2026-10-23T09:30:50-07:00 (America/Los_Angeles).

Both original V102/V10320k runs, seven matched evaluation stages and full-frame
GFX export completed successfully. Independent aggregation reproduces99,232
photo/procedural rows and1,296 camera rows; all eight complete RGB16 TIFFs were
rehashed and reopened. All102 native board cells and four resized context
views were actually viewed. Earlier pending-at-creation receipts and private
snapshots retain their original bytes; a separate completion receipt closes review.

V102 is the current quality/training baseline:36.67951dB full427,+.17604dB over
V101,425/427 source means improve. Known/unseen CFA means54.23709/53.97177dB.
V103 has36.68091dB (+.00140 over V102; source interval includes0), but lower CFA
means and weaker tested carrier response. ADC maximum flat-color bias is59.23DN
for V102 versus1074.49DN for V103. Neither resolves fine high-noise texture,
soft foliage or saturated-light structure. Current docs and README reflect
useful gains without demanding every-diagnostic significance gates.

Published two native noisy/restored/exact-GT triplets per improved checkpoint,
known/unseen nonexact-AHD comparisons, weak carriers, flat colors and six GFX
regions from complete blended frames. README foliage/fence now use complete
V102 frames. PSNR plot contains43 endpoints/20 sources; independent audit proves
all41 prior points/19 source records unchanged. Current V102 full-frame inference/
blending took202.31s in this shared-machine FP32 run, excluding loading/writes.
The10s goal and broad real-photo quality objective remain unmet.

Next continue exact V102 EMA on reviewed90,872 Commons sources (2,395 neweligible),
retaining six ROIs and zero optical blur before any further intervention.
No larger-corpus quality benefit is claimed before training/evaluation.

Linear DNG and optional pre-restoration hot-pixel repair were merged and pushed
in77328d1, with66 tests passing and two CUDA-only skips, including actual native
darktable integration. Repair was off for these comparisons.

Validation for this publication:79 targeted existing tests pass, Ruff passes,
native cell hashes match exactly, and local documentation links resolve.

[Current report](../docs/v102-v103-quality-review.md) ·
[Completion and audit](../docs/results/v102-v103-quality-complete-v1.json).
