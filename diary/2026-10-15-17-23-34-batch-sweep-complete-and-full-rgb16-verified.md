# Completed batch sweep and verified full V30 RGB16

All10 mixed-training cases completed, one shared source snapshot. Warmed mean
images/s (two repeats) for batch4/8/16/32/64:22.52/24.56/26.14/26.42/26.27;
peakCUDA2.23/3.72/6.94/13.39/26.28GB. B16 is within1.1% of B32 mean, with about
half its allocation and16% greater throughput than B4. Choose16 for the next
quality trial, LR unchanged. Two shared-machine repeats are not a confidence
interval or proof of a unique optimum/convergence improvement. Full results in
 docs/results/training-batch-sweep-v1.json and docs/training-pipeline.md.

Actual4x->augmentation->2x Commons/DINO BF16 CUDA backward completed with finite
FP32 output and nonzero adapter gradients. Rebuilt wheel matches exact final
CLI/data/train/prepare code and all four license notices.

Full102MP V28-5k/V29-1k/V30-1k/RawNIND restoration completed in33.26/34.77/33.70/
18.00s, single successive shared-machine run. All8 linear/sRGB TIFFs independently
rehashed, dimensions8746x11662x3 anduint16/16bits/channel checked, sRGB ICC tags
verified and sampled code counts>256. Published full native foliage/fence,
sky/building and matched methods with correctly labeled independentISO100ref.
V30 retains visible mesh but soft detail/irregular wires; speed10s and final
quality remain unmet. Receipt docs/results/gfx-anchored-v30-full.json. README now
uses full-frame experimental GFX crops rather than standalone context outputs.

The post-sweep workflow began full frozen-selection4x preparation only after
GPU reviews completed. Source splits unchanged, originals read-only, standing
GFX scene/siblings excluded. Log.cache/prepare-commons-bin4-full.log; original8x
manifests remain fixed for current training/validation. Background QI download
continues with512GiB reserve; newly downloaded images still need their separate
extension audit before being trained on.

Started V31 from frozen V30step1000, retaining model/AdamW/EMA/RNG, deliberately
switching batch4->16. First1001 row finite; manifest/model/LR/mixture unchanged.
Global sample indices now follow batch16. Stop at2000 (1000more updates,16000
examples) and run pairedknown/unseen, synthetic16 and nativeGFX review. This is
not an equal-sample comparison or proof that batch alone improves quality.
Source/config/startup receipt records the transition. No automatic extension
beyond that review point. The source cache, checkpoint and final evaluation
remain separate from GFX; no target fitting.

Next avoidable-work candidate: in vst.expectation_table, the large Poisson
probability matrix depends only on fixed count/mean grids but is regenerated for
every read_e. Cache that invariant and verify exact tables/output plus measured
conditioning/training costs before changing code. Native-RAW4x cache and its
pre-reduction augmentation extension also remain open. Goal stays active.
