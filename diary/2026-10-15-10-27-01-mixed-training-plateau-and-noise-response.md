# Mixed training plateau and noise response

V9/V10 completed their matched 5000-step trials. Standardized features add only
~0.03 measured-sensor dB and do not reduce flat residual variation. Keep that
experimental option disabled in the mixed recipe.

V11 completed its 5000-step review stop. Measured PSNR is 51.6932 dB on the four
known-sensor scenes and 50.9835 on five M100 scenes, nearly unchanged from its
1000-step values. Full 427-photo synthetic PSNR/SSIM is 31.3749/0.91803, slightly
below the additional-Common-only control's 31.4285/0.91851. Do not blindly resume
the same recipe just because 20000 steps were planned.

Added evaluator-only variance/window diagnostics with explicit receipts; physical
input data and reference/classical-baseline settings are retained. Variance×2
improves measured PSNR to 52.2278/51.6196 and rendered auxiliary PSNR to
38.0131/36.1273. Variance×4 is worse. Neither reaches RawNIND.

Checked input Haar estimates against same-color measured-reference residuals in
flat blocks. Per-capture empirical/estimated variance medians span 0.872–1.081.
This does not support blaming a large calibration scale error. Reference noise,
subpixel registration imperfections and selection remain limitations. Replacing
the model's prior window7 by15/31 worsens aggregate quality; those overrides are
not promoted. Removing DINO context at inference worsens flat variation and is
also rejected; that diagnostic is not a matched training ablation.

All training runs are at their intended terminal review points. The next useful
control is precision/learnability: BF16 activations may lose weak RAW variations
against larger metadata offsets. Test that hypothesis against IEEE FP32 rather
than assuming another architecture change will solve it. Full scope remains
incomplete: real denoising still trails RawNIND, and final tests/quality/speed are
not established. All 149 tests and Ruff passed before these evaluator-only flags;
39 paired training/evaluation tests pass afterward.
