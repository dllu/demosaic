# Saved-parent color gain screen and full shared-forward photo test

After completing/pushing the failed V74/V75 first1k review, tested the existing
RawNIND per-channel observed-CFA least-squares expression on unchanged mature
V63 original20k predictions. Fixed whole-native256 fits, FP64 sums/multiply,
FP32 output; no masks/clamps/bounds/shrinkage or target/reference access.

All1176 saved grid observations completed in a CPU-only pass with zero model
forwards, CUDA initialization or new noise draws. Bright moderate/high saturation
mean maximum-channel bias falls88.2%/66.5%, with both worst cases lower.17/18
group means decrease; dark noisy neutral rises slightly. The prospective25%
bias-reduction/no-worst-case-increase screen passes both groups, allowing a
fresh photographic test, not model promotion. Spatial variation remains visible.
Independent NumPy phase slices/dot products check all1176 fits: gains maximum
2.15e-14, corrected FP32 pixels5.96e-8. Old case metrics reproduce exactly.
All14 native flat triplets/28 cells were actually viewed at original resolution.

Implemented frozen shared-forward full427+16 procedural CUDA FP32 evaluation
with original protocol/noise/crops, B4/channels-last,24GiB allocator cap and
2h limit. Exactly one network forward supplies original/corrected outputs;
three fresh classical controls accompany the pair. The native256 per-image gain
is exploratory; a whole-frame method must separately validate one global gain
and RGB16/export/seam/timing behavior. No training/NN/inference defaults changed.

Seven focused tests pass in2.55s, including separate/all-CFA physical fixtures,
both greens, signed/unbounded and zero inputs, and a counted single-forward
fixture that rejects GT access. Ruff and git diff --check pass. Full-test plan,
worker and43+ package/helper sources were frozen before launch. The live
PID3778801/creation1792341282.26 was verified after308 actual forwards/44 sources.
The complete443-source grid requires3108 network forwards and62020 score rows.

All four first fixed photo triplets/eight unique cells were actually viewed.
Canopy broad color moves slightly toward GT but fine cords remain missing;
building/cloud detail looks nearly identical. Published both corrected native
GT examples, parent/corrected board, source/checkpoint/noise/ROI/display bindings
and dated execution evidence. Final producer PNG/metadata revalidation remains
required after successful full-test exit. Full aggregate/camera/sensitivity and
real/full-frame quality decisions remain pending; no default/promotion.

The new photo plan requires at least.05dB mean gain with a positive source
interval, at most.0001 SSIM regression and at most.05dB known/unseen CFA losses,
plus complete native/color/highlight/sensitivity review before considering a
full-frame promotion. The failed V74/V75.03dB training threshold stays unchanged;
those arms are not extended. The project goal remains active and unfulfilled.
