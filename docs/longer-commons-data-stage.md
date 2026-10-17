# Longer matched Commons-data comparison

V63 is training the control arm; V64's expanded-data arm follows on the same
GPU after it exits. This tests more scene diversity with a longer training
schedule after [V61](sensor-mean-v61-first1k-review.md) and
[V62](sensor-mean-v62-first1k-review.md) failed to improve the overall color/detail
tradeoff. **No new quality gain is established yet.** V43 remains the working
reference, with the standing real-camera tests and protected-final boundary intact.

[Actual launch, frozen plans/configs/source, production startup and CUDA checks](results/long-commons-v63-v64-first4k-launch.json).
[Control recipe](../configs/dino-convnext-wide-long-control-b16-v63.yaml).
[Expanded recipe](../configs/dino-convnext-wide-long-expanded-b16-v64.yaml).

| Setting | V63 control | V64 expanded |
| --- | --- | --- |
| Commons training sources | 40,170 | 66,934 |
| Commons cache | Original complete 4× | Reviewed complete extended 4× |
| First review / original planned updates | 4,000 / 20,000 | 4,000 / 20,000 |
| Other settings | Shared | Shared |

Both start from completed V60 wide-palette step4000 **EMA**, SHA256
`1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e`,
with fresh AdamW/EMA, seed 49, LR 1e-5, warmup 200, batch 16/native 256 and BF16.
This is a deliberate new stage; the original V60/V62 runs and schedules remain
immutable. Parent comparisons include additional updates and an optimizer reset;
only the two new matched arms isolate training-data membership.

The 32,904,704 restoration parameters train; the pinned DINOv3 backbone remains
frozen. Both retain the 8-stop palette, loss weight 0, 128 native captures from
106 scenes, original 32 paired scenes, all source fractions and noise/ADC,
4×→geometry/PSF→area2, worker counts and original 8× validation. The expanded
manifest SHA256 is
`7ed635903e4dd698081475a3667c8a14bb3b9f5f628a0917a5e336406faaecde`.
Its full 4×/8× cache and membership checks are in the
[completed corpus review](commons-incoming-v3.md). The new 75,806-source v4
membership stays separate while its 4× caches are prepared.

The actual parent/source/data CUDA fixture executes seven discarded updates per
arm using production seed 49, batch 16/native 256/BF16 and the 20,000-step
schedule. It covers Commons, native and paired domains. All 91 model/91 EMA
tensors and 89 AdamW states are finite. Two portable EMA photo predictions match
reconstruction from the raw saved state exactly. Both fixtures share domain
choices/LRs and all native/paired input hashes; real Commons batches differ as
expected. Peak CUDA allocation is 7.200 GB, not a production throughput result.

Fixtures disable data workers, force real Commons photographs instead of smooth/
procedural examples, and use two validation images to check the changed data
path. Production retains its original fractions, workers and validation. No
training/optimizer/EMA implementation changes were made; the same frozen source
already has CPU restart checks. These fixtures do not establish convergence,
quality, deterministic CUDA optimization after restart or a new CPU restart result.

The controller verifies preceding owner exits and the completed V62 review,
source/config/data guards and successful fixture before launching. It runs each
arm only to 4,000 under its original 20,000 schedule, freezes complete model/EMA/
AdamW/RNG state, and checks all 161 logged domain/LR choices and unchanged-domain
input hashes. Commons hashes may differ because membership differs. Further
updates require a complete native/photo/paired/hue/GFX review and preserve whole
state and the original schedule; there is no automatic continuation or promotion.

Controller PID 1988162, creation 1792207826.66. Status:
`/mnt/external/demosaic/runs/long-commons-v63-v64-first4k-workflow-v1.json`.
Plan and archived controller/configs:
`/mnt/external/demosaic/benchmarks/long-commons-v63-v64-first4k-workflow-v1/`.
Log: `.cache/train-long-commons-v63-v64-first4k-v1.log`.
Inspect actual PID/creation and child status before acting; do not start duplicates.

Reports must include at least two native noisy/denoised/exact-GT photographic
triplets and DSCF3879/3880 sky/building/foliage/fence crops, with accurate non-GT
labels for independent real references. No protected-final model score is used.
The desired real-photo quality, SOTA and 100 MP within 10 seconds remain unresolved.
