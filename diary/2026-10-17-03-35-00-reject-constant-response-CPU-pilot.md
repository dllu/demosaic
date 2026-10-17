# Reject an input-only constant-response hypothesis before training

While the real RAW batch sweep ran, tested one prospectively fixed CPU method:
unchanged mature V60 prediction minus its response to the observation's own
constant per-color RAW mean, plus that calibrated mean. Same variance/noise/
WB/matrix/CFA, separate corresponding DINO forwards, no reference fitting.
No model source, weights, production inference or GPU queue changed.

Native256/B1/FP32/two threads on two exact-target photo observations and four
saved noisy color fields. All four native64 clean-constant/CFA checks are exact,
but the predeclared no-RMSE-regression rule fails on photo1, neutral and blue.
Blue RMSE .002786→.036835; photo1 sRGB PSNR35.258→34.782. Some other cases improve,
so a single favorable color would have been misleading. Do not integrate/tune/
train this specific correction; clean invariance does not guarantee noisy bias.

Actually viewed all12 native triplets in two small groups. Independently rebuilt
24 camera metrics from saved F32 arrays with NumPy64; all match. All noisy/GT
pixels match between methods. Published a short failed-pilot report with four
unchanged photo PNGs and full source/ROI/noise/checkpoint/display receipts.
No SOTA/broad quality/full427/GPU-speed claim. Two forwards would also cost more.
