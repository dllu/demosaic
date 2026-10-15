# V16 review and residual scales

Previous goal turn made progress: V15 actual trained/evaluated model, complete
102 MP RGB16/sRGB16 outputs, source/weight receipts, reports and pushed commits.
Revalidated V16's live process before observing its completed 5000-step run;
no restart on timeout. V16 known/unseen measured-CFA PSNR is53.27466/53.07857,
up0.17490/0.22676 dB over V15. Scene-bootstrap gain intervals
[.04320,.35989]/[.15510,.29341] use only4/5 development scenes. RGB PSNR
39.15836/37.65963 and SSIM.92152/.90718 improve too. RawNIND still leads primary
PSNR by.79394/.48363 dB. Full427 synthetic photo PSNR/SSIM31.48800/.923018,
procedural16 sources30.56577/.922656. Native crops retain visible errors.

V16 complete GFX frame restored to11662×8746×3 linearRGB16 and ICC-sRGB16.
Verified unsigned16 tags, dimensions,10990/39759 distinct sampled code values
and sRGB ICC profile.53.28s restoration overlapped V17 training and excludes
decode/load/render/encode; not an idle benchmark or10-second target attainment.
Peak CUDA.804 GB is not total unified memory. Updated README/native GFX crops;
RawNIND comparison retains the prior full-frame outputs at identical settings.

Exact synthetic flat-target scale decomposition separates channel DC bias from
centered residuals. At level.01, V15 reduces total sigma.00064178→.00029864
relative to V11, while32/64-pixel mean error is nearly unchanged. RawNIND has
lower absolute errors. A larger retained-power fraction alone is not a failure:
fine-noise removal raises the fraction. Published absolute-error curves, native
GT triplets and receipts; no real GFX pixels are used as training targets.

Full project quality and protected-test gates remain open. RawNIND remains
better on real development.160 tests pass; source/figure/PNG checks recorded.
