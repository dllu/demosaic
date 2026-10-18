# Complete V74/V75 objective first1k review

The full FP32 study and CPU closure are complete. V75 log-MSE gains.02025544dB
photo PSNR over its matched V74 control, source-bootstrap95% interval
[.00650688,.03617744]. The original.03dB continuation minimum fails, as do the
fixed418/416-source sensitivities. Both stop at1k; neither is promoted or
extended through its remaining3k schedule. V43 remains the working reference.

Known/unseen CFA gains are.06518025/.03417706dB; unseen interval crosses zero.
Photo SSIM, chroma, gradient and highlight-boundary errors move slightly against
log-MSE. Bright saturated flat fields improve over the new control but stay
close to parent; the moderate-color worst case worsens against parent. Fine
carriers/cords remain suppressed. Standing GFX sky/building/foliage/fence and
supplementary sign/platform crops show similar mature-model behavior, without a
clear broad gain. DSCF3880 ISO100 AHD remains a separate qualitative reference,
not GT. No new full-frame quality/timing claim is made for ineligible models.

Actual native inspection covers67 triplets/111 unique cells. Early photo and
camera pixels/metadata were rechecked after successful inference producer exit.
Final GFX/analytic boards match already viewed board hashes exactly. The first
combined call for the remaining three boards was truncated, so it was not
counted; hue/extra-hue/highlights were subsequently opened individually at
original resolution. The complete manual receipt records this distinction.

All108 primary comparisons/27 classical witnesses pass, every witness exact.
Independent saved-hue Torch64 checks cover3,528 predictions/21,168 metric fields
(some vectors), maximum5.55e-16. Color summary checks54 groups/648 scalars,
maximum3.47e-18. Analytic checks1,344 cases/84 groups/2,256 scalars,
maximum2.22e-16. Sensitivity audit independently reaggregates215,208 raw metrics,
7,686 source scalars and540 comparison scalars; maximum3.55e-15. These are
arithmetic/coverage checks, not new training-repeat or generalization evidence.

Published the full review and final registry with all source/checkpoint/noise/
ROI/display bindings, plus five native boards and four GFX foliage/fence
triplets. Retained original progress/interim evidence unchanged. Added the
CPU-only closure operator and six gate tests;6 passed in.02s, Ruff passed,
report local links passed and git diff --check passed. The terminal review and
closure owners/final child were verified absent; no CUDA process remains.

Root/external available storage is336/503GiB with128/500GiB reserves. Downloads
remain stopped. No originals or PROMPT.md were changed. The project goal
remains active: SOTA, decisive real-photo superiority and100MP under10s remain
unmet/unproven. The failed first1k continuation gate is not weakened.
