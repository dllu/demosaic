# First pyramid/RAW-innovation review complete

Both V24/V25 processes exited successfully at the predeclared 1000-step review
(sessions6699/71267 terminal). Paired/synthetic evaluation session92859 and
flat/GFX session25355 also exited successfully. No training is still running.

All 41 sampled input/target hashes, CPU/Python/CUDA RNG states, archived training
source and initialization match. All original model/EMA values are bit-identical
to parent V16. Only the new branch changed. Tests already passed (182), with no
subsequent implementation edits. Frozen checkpoint/source receipts retained.

Known/unseen primary PSNR: V16 53.27466/53.07857, control V24 53.28219/53.07837,
RAW V25 53.26126/53.07230. Raw-minus-control −0.02093/−0.00608 dB; 95% scene
bootstrap intervals cross zero. Auxiliary rendered metrics also favor control.
The 64-photo screen favors raw access by +0.01158 dB over control (interval
[+0.01043,+0.01281]), but this is small and not the full 427-photo panel.
Eight procedural sources give 29.21752/29.22141 dB for control/raw.

Exact-flat level 0.01 centered sigma is 0.00023195 parent, 0.00023225 control,
0.00024438 raw. The 32/64-pixel residuals are essentially unchanged. Visually
reviewed paired and new-pair GFX foliage/fence: detail loss and color speckling
remain. All four GFX regions and four methods used identical 512-pixel contexts,
shared +2 EV, native 160-pixel panels and the DSCF3879/DSCF3880 pair. These are
crop-only outputs, distinct from the earlier blended full-frame report.

Neither candidate is promoted. README retains reviewed V16. Report includes two
paired native noisy/denoised/AHD-reference triplets per candidate, four matched
V16/V25 GFX texture triplets, complete metrics/weights/ROI/noise/display receipts
and matched observations. AHD and independent f/5.6 capture are not exact RGB GT.
No final-test evaluation or full-frame speed claim. Quality/speed goals remain
open. These results test one short frozen-parent recipe, not all RAW access.

The next available experiment should address the observed coarse error more
directly, such as scale-aware supervision against a matched original-loss
control. More branch capacity alone has not established useful coarse denoising.
See `docs/pyramid-refinement.md` and `docs/results/pyramid-v24-v25-1k-review.json`.
