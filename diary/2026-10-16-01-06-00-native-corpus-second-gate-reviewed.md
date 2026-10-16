# Review the native-corpus second gate and retain its tradeoffs

The previous goal turn made progress by adding the optional low-rank DINO
implementation and CPU gradient/checkpoint/restart evidence. This turn rechecked
controller PID1038531 and both queued jobs against their actual live processes.
The corpus controller completed all training and review at07:58:11UTC, then
exited. All three runs stop at step2000; all65 shared logged Commons/paired
observations match across their82 logged training observations each.

V43 step2000 reaches full427 photo PSNR34.89934/SSIM.957126: +.19536dB over its
own first gate,95% source interval[+.15173,+.23035], and +.08870dB over matched
V37 at2000,[+.06747,+.11833]. Unseen measured-CFA improves .07632dB over its
first gate,[+.01494,+.14043], reaching53.80606. Known primary falls .03021dB
with interval crossingzero; unseen AHD SSIM falls from.922620 to.921579.
Its unseen advantage over V37 is only.02953dB with interval crossingzero.

Procedural PSNR falls .56471dB,[−1.29892,−.09554]. A small group of sources drives
the loss. Synthetic-13 loses4.8033dB overall and9.112dB in ADC-only conditions;
synthetic-0 loses1.8193dB, synthetic-10 1.2866dB and synthetic-1 .9386dB. These
large low-noise failures are recorded per source/condition in the receipt.
Investigate them before extending any current arm to3000. Do not hide the
regression behind the photographic mean.

[Full review](../docs/native-corpus-2k-review.md) and
[complete measurements/crop receipt](../docs/results/native-corpus-2k-review.json).
All30 new native160px triplets verify by SHA, dimensions, panel coordinates,
source/ROI/noise/display metadata and identical noisy/reference panel bytes.
Each of the three new checkpoints has two exact-synthetic-GT triplets. Real
paired AHD and separate GFX ISO100 references retain accurate non-GT labels.
All six new complete102MP RGB16 TIFFs verify SHA/size/dtype/shape/16bit/sample
codes; the three sRGB outputs carry ICC profiles. GFX restoration takes
34.08/33.80/33.51s for V37/V39/V43, successive shared-machine observations.

Visual inspection compared first/second-gate synthetic, unseen and GFX crops
plus cached channel-calibrated RawNIND foliage/fence. Fine fabric threads remain
missing and cloud/leaf texture soft. The wire mesh remains more legible than
RawNIND's repeating blur, but first/second V43 gates look close and an isolated
colored point persists. No decisive visual gain or broad RawNIND/SOTA margin.

V43 step2000 becomes the photographic experimental reference, with these
tradeoffs prominent in the report/README. Its immutable known-evaluation
snapshot SHA is
`0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5`.
New alias `/mnt/external/demosaic/models/v43-step2000.pt` points there. The
first1000 alias still verifies its original8ee3 hash. README keeps two exact-GT
triplets and standing full-frame foliage/fence examples.

The second publication driver is archived under runs as
`publish_native_corpus_2k_v2.py`, SHA
`9fa1f8b8ddf8be19d7bb62d5c0e4e0564c68636439e4cb7d3908745ed247f5aa`.
The first prepared driver remains archived unchanged. Publication uses completed
frozen reports; its final interpretation and selection were reviewed separately.

Batch queue PID1048124 began its actual4× Commons/native128 sweep only after
the corpus controller exited. GPU-check queue PID1086009 waits for the complete
batch sweep and its process exit. It then runs the352-test CUDA suite and a
genuine full-model BF16/FP16 all-CFA identity/backward/full-state-resume fixture.
Its source is frozen atca846a0 in `.cache/dino-adaptation-worktree`; it does not
modify the V43 benchmark checkout. No new quality training starts yet.
[GPU queue receipt](../docs/results/dino-lora-gpu-checks-queue-v1.json).

Next: publish the batch sweep and GPU results; investigate the low-noise pattern
failure with controlled inference diagnostics before another quality trial.
The fresh DINO control remains prepared. Commons downloads continue separately;
all experiments retain their frozen source selections. Full objective unmet.
