# Fresh mixed16 RAW quality trial

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

The [frozen V72/V73 trial](results/packed-isotropic-mixed16-trial-launch-v1.json)
uses the full original Commons/native/paired training mixture. Both genuine
12-update prefixes passed model/EMA/Adam, common initial state/RNG, actual
source/noise and FP32 portable-reload checks. Both V72 no-DINO and V73 DINO
have completed their2,000-update/32,000-example gates. The
[independent final-boundary audit and actual handoff](results/packed-isotropic-mixed16-first32000-training-boundary-v1.json)
pass; both training workers/controller have exited. The
[completed full FP32 review](packed-isotropic-mixed16-first32000-review.md)
finds +0.50510/+0.41568dB photo gains over older equal-example controls, but
strong residual grain and151.54/169.39s FP32 full-frame restores prevent
promotion. V43 was the reference for this experiment. The earlier
[matched camera and native-crop interim review](packed-isotropic-mixed16-matched-camera-interim.md)
finds only small DINO gains (+0.01779/+0.03839dB measured-CFA known/unseen),
with both new arms substantially behind mature models and RawNIND.
All automated audits and146 native-triplet views are now complete; the review
owners have exited. The quality decision selects an isolated continuation to
10,000 original-schedule optimizer updates/160,000 examples, preserving all2k
evidence. The [isolated continuation is now running](packed-isotropic-mixed16-quarter-training.md),
with its [complete review queued](packed-isotropic-mixed16-quarter-review-queue.md)
behind the exact training owner.

The [current-versus-EMA CPU check](mixed16-current-EMA-CPU.md) finds only
0.03–0.17dB current-weight gains on the same two fixed photos, with strong grain
in both policies and no clear new GFX foliage/fence advantage. The review kept
its original EMA policy; this selected diagnostic does not explain the large
gap to mature models or establish convergence.

A [genuine trained-state CPU restart preflight](mixed16-trained-state-restart-CPU.md)
now matches four updates against2+2 exactly for both2k parents, including
Adam/EMA/counters/CPU RNG. It uses cropped64px training-only fixtures and
does not exercise CUDA or itself decide on a continuation. All learned test weights
are discarded; the production training gate and quality review remain unchanged.

The [complete V72 development-camera CPU check](packed-isotropic-mixed16-V72-camera-CPU.md)
now improves known/unseen measured-CFA PSNR by2.8302/2.1418dB over original
V71 at equal32,000 examples, with all nine scene gains positive. It still
trails Wiener7+Malvar and RawNIND substantially. The matched CUDA camera panels
now confirm that ordering; competitive final quality is not established.

The [execution sweep](mixed-optimizer-batches.md) chose four B4 forwards for an
effective16-example update. Gain32 applies to neural RAW features and1/32 to
the learned residual; physical output/loss units remain unchanged. Both arms
use IEEE FP32, channels-last, LR2e−4, clipping1 and identical data manifests.
Only genuine frozen DINO presence/fusion differs within this new pair. Relative
to older V70/V71, the candidate also changes precision and optimizer grouping;
it is not a single-factor comparison against those older models.

| Counter | First prefix | First quality gate | Full planned horizon |
| --- | ---: | ---: | ---: |
| Optimizer updates | 12 | 2,000 | 40,000 |
| Original B4 source steps | 48 | 8,000 | 160,000 |
| Example draws | 192 | 32,000 | 640,000 |

| Completed first-gate arm | Checkpoint SHA256 |
| --- | --- |
| V72 no-DINO | `8d67375e2169adb88f7dcdafd253e23642eb0d87b1dc2d79416cb0f22320416a` |
| V73 DINO | `43c10f2a0af38761f9418f19c725edc4129284e76b5b2da89f66c184d1f643e1` |

Both final checkpoints retain finite model/EMA and852/863 Adam states at2,000,
complete RNG and original40,000-update schedules. Genuine prefix-to-final
restore and portable FP32 reload checks pass. All82 logged mixed groups,
noise fingerprints, LRs and example counters match across arms; each also
matches82 overlapping original V71 source/noise observations. The common
source bundle remains`fabd0b781938e156a6dcf89fb429a0a0c7c727e9c1acdb38c434dd201a81ebae`;
official frozen DINO remains unchanged and gradient-free. This establishes the
training boundary and review release, with quality and continuation decisions pending.

Warmup is500 updates/8,000 example draws. EMA cap is`.999**4`, with the
existing adaptive startup retained. Each original B4 group uses its own
unchanged domain/source indices, degradation RNG and supervision reduction;
one gradient clip/Adam/EMA update follows their mean loss. Data admission stays
at40,170 Commons sources,128 native captures/106 groups and32 paired scenes.
The standing GFX scene/siblings and protected-final scenes remain outside training.

The first12 updates are part of actual training. Immutable prefix checkpoints
are archived before full-state continuation. Before its first resumed backward,
the frozen worker checks restored model, Adam moments, Torch/Python/CUDA RNG.
The actual step13 event confirms that continuation path executed. Both prefix
EMA reloads are bitwise equal on the recorded FP32 fixture, with finite852/863
Adam states at12 and unchanged official DINO hash. The first16 actual source/noise
hashes match across arms. The startup audit also compares available logged source
steps with V71's original log and finds identical domains and observation hashes.

The immutable prefix archive references are authoritative: producer `last.pt`
references describe their source-time files and were replaced at the quality
gate. The launch receipt records the active controller/child identity and a
snapshot of progress; it is not a live progress counter.

Training stopped at the32,000-example gate. The completed first-gate report
includes full held-out/camera/analytic/color checks, at least two native100%
noisy/denoised/exact-synthetic-GT crop triplets per model, and standing GFX
foliage/fence comparisons with the ISO100 capture labeled an independent
qualitative reference. There is no automatic extension, protected-final scoring
or promotion. The V43 README examples were retained at the time.

The [frozen quality-review queue](results/packed-isotropic-mixed16-review-queue-v1.json)
waited for the exact training controller and final child to exit successfully.
Its independent preflight rechecked both immutable prefix states and their
source bundles, verified38 input files and181 frozen files, and refused to
release inference while training remained live. The implementation has59
focused passing CPU tests. Both exits and the independent final audit subsequently
released the review. All panels, statistical/artifact audits and native views
are complete, without promotion.

Primary panels will recompute six checkpoint models in IEEE FP32: V72/V73,
working V43, mature V63, and original V71/V70 at8,000 B4 updates. The latter
controls saw the same32,000 examples as the new2,000 effective16 updates;
the candidate changes units, precision and optimizer grouping together.
Two observed-CFA RawNIND adapters and three classical methods complete the
11-method panels:792 known-camera,990 unseen-camera and136,444
photographic/procedural observation records. The final boundary audit also
checks82 logged original V71 observation hashes/domains against the new data
steps, rather than equating optimizer-step numbers across batch sizes.

Auxiliary panels retain V72/V73 and V43/V63:2,240 analytic records, six full
GFX restorations including RawNIND with12 RGB16 exports, three cached cameras,
128 selected CPU color predictions and4,704 fresh hue-grid predictions. The
FP32 hue run does not reuse earlier FP16 predictions. The statistics include
13 model comparisons per primary panel,156 metric comparisons and117 fixed
source-cohort sensitivities. These source bootstraps do not measure training
repeat uncertainty or certify scene independence.

The queue saves native160-pixel triplets and checks source/ROI, noise,
checkpoint hashes, exposure, unchanged noisy/reference panels and RGB16
exports. Full-frame timings will be single shared-machine observations.
Actual visual inspection is now complete and the decision keeps both models
unpromoted. Successful automation alone cannot promote these models.

The first gate is also a much shorter training run than the related published
synthetic Bayer experiment. [JD3Net §4.4](https://arxiv.org/html/2601.00703v2#S4.SS4)
reports one million updates with batch20 and128-pixel patches for its larger
model. Its [pinned author configuration](https://github.com/cory-fan/jd3net/blob/47489cbe3eba746e13ad8be8898956d7895f1835/demosaic/options/train/Demosaic/Isotropic64_imagenet.yml)
specifies AdamW LR`.001`, betas`.9/.9`, no weight decay and PSNR loss. That
configuration implies20 million patch draws; our first gate has32,000 and
the planned full horizon640,000, at256-pixel patches with other losses,
noise, data and architecture. These counts do not establish comparable compute
or recommend transferring that optimizer. The paper's smaller-model patch/
batch settings also differ from its checked-in small configuration. See the
[primary-source inspection receipt](results/jd3net-training-budget-context-v1.json).
The present schedule stays fixed, and the early gate cannot establish convergence
or rule out later improvements from training.
