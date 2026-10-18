# Fresh mixed16 RAW quality trial

The [frozen V72/V73 trial](results/packed-isotropic-mixed16-trial-launch-v1.json)
is running on the full original Commons/native/paired training mixture. Both
genuine12-update prefixes passed model/EMA/Adam, common initial state/RNG,
actual source/noise and FP32 portable-reload checks. The no-DINO continuation
has resumed beyond its prefix; DINO follows serially. Photographic quality and
full-frame performance remain unmeasured for these candidates.

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
references describe their source-time files and will be replaced at the quality
gate. The launch receipt records the active controller/child identity and a
snapshot of progress; it is not a live progress counter.

Training stops at the32,000-example gate. The first public performance report
must include full held-out/camera/analytic/color checks, at least two native100%
noisy/denoised/exact-synthetic-GT crop triplets per model, and standing GFX
foliage/fence comparisons with the ISO100 capture labeled an independent
qualitative reference. There is no automatic extension, protected-final scoring
or promotion. Existing V43 README examples remain the working reference.

The [frozen quality-review queue](results/packed-isotropic-mixed16-review-queue-v1.json)
now waits for the exact training controller and final child to exit successfully.
Its independent preflight rechecked both immutable prefix states and their
source bundles, verified38 input files and181 frozen files, and refused to
release inference while training remained live. The implementation has59
focused passing CPU tests. This is preparation evidence, with no new quality
result yet.

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
Actual visual inspection and the quality decision remain subsequent work;
successful automation alone cannot promote these models.
