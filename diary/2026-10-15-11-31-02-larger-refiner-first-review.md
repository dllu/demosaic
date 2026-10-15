# Larger refiner first review

V16's width48/eight-block branch has144,072 trainable parameters versus V15's
27,696; the base V11/DINO remains frozen. Same data proportions/loss/LR, but
different model initialization changes the RNG sequence, preventing a strict
matched-sequence capacity ablation.

At1000 steps, real known/unseen measured-CFA PSNR52.92099/52.60448 improves over
V15's same-step52.52635/52.15919. Auxiliary SSIM.91375/.88986 also improves.
The matched-input64-photo screen gives31.89746/.922292, procedural8 sources
29.10436/.905848. This is not a full427-source comparison or a promoted model.
Source/weight receipts and two native noisy/V16/AHD-reference triplets are in
docs/wide-refinement-review.md. Started a resumable extension to5000 after this
review; the checkpoint and original planned5000-step LR schedule are preserved.

V15 step5000 remains the latest fully reviewed candidate. RawNIND still leads
real quality. No protected-final-test or GFX evaluation-scene training; no source
photo writes. The full project goal remains active.
