# Photo-trained refinement and full GFX outputs

V15 completed step1000 review and a resumed extension to step5000. Only the new
27,696-parameter RGB correction branch trains; original V11 restoration/DINO
weights remain frozen. Same physical units and losses; 50% independent paired
RAW training batches, 50% Commons simulation with normal structure/flat/detail
mix. The flat-only V14 failure is not promoted. This is a different training
distribution/budget, not a matched ablation of flat-only versus photographs.

At step5000, scene-balanced known/unseen measured-CFA PSNR is 53.09976/52.85180,
up1.40657/1.86830 dB over V11. Corresponding scene-bootstrap gain intervals
[.82555,2.08422]/[1.44965,2.23075] use only4/5 scenes, so generalization remains
limited evidence. Auxiliary RGB PSNR38.97516/37.31596 and SSIM.91754/.89840 improve
too, but RawNIND still leads primary PSNR by.96884/.71039 dB. Full427-photo
synthetic PSNR/SSIM31.44165/.921748 improves slightly over V11; procedural16
sources30.49185/.919789. Default-protocol classical crosscheck across37212 rows
agrees within7.63e-6. Source/checkpoint/manifest hashes and bootstraps retained.

Added full-frame mode to scripts/report_raw_pair.py. Both V15 and RawNIND restore
the complete101.996 MP cached GFX image before native cropping. Each produced
linearRGB16 and ICC-sRGB16 TIFFs at11662×8746×3. All four were checked for unsigned
16-bit encoding and thousands of distinct sampled values; both sRGB profiles
present. Common+2 EV/WB/matrix, no per-panel adjustment. Restoration28.89/16.35s
overlapped synthetic evaluation, excluding decode/load/render/encode; not idle
benchmark evidence and not the10-second goal. Peak CUDA.634/1.374 GB, not total
unified system memory. Crop-only refactor PNGs are byte-identical to prior V11.

Native report crops visually inspected: less grain but remaining low-frequency
color blotches, missing threads/fine structure, and soft edges. RawNIND's GFX
sky remains cleaner. ISO100 f/5.6 scene is only a qualitative reference. No
pixelwise GFX scoring and no evaluation-scene training. README illustrations
updated to V15; full reports include exact synthetic GT and accurately labeled
real references, source credits and coordinate receipts. Quality goal remains
unmet.156 tests pass, Ruff clean. V16's larger branch is a separate trial.
