# Mature-parent objective comparison on the cleaned expanded corpus

V74/V75 are a new bounded quality experiment, **not improved or promoted models**.
Both initialize from genuine V63 original20k EMA and train on the reviewed
84,867-source Commons corpus, original128 native captures/106 groups and32
paired scenes. Only the reconstruction objective differs between the arms.
Both stop at1,000 updates of an original4,000-update schedule for complete
quality/native review. No automatic continuation follows.

Both1k boundaries are now complete. The [independent boundary and first native
views](reconstruction-objective-first1k-review.md) are published while the full
FP32 review runs; they do not yet establish a trained-quality gain.

[Frozen plan, exact source/data/checkpoint hashes, actual CPU/CUDA engineering
results and verified-live launch snapshot](results/reconstruction-objective-preparation-v1.json).
The snapshot is dated; inspect its actual controller/child PIDs and creation times
for current execution status. The [mature quality limitations](long-commons-v63-v64-original20k-review.md)
and [negative fresh RAW-backbone review](packed-isotropic-mixed16-quarter-review.md)
motivate returning to the stronger pretrained RGB/DINO model.

## Question and loss definition

The mature network still shifts some colors and misses fine detail. On one
selected fabric example, [mean/coarse error explains most of a later regression](control-original20k-error-decomposition.md).
This does not identify a general cause. The existing objective averages robust
absolute reconstruction errors; the photographic metric averages per-image
PSNR. A controlled change tests that mismatch without adding a new architecture.

The recent [JD3Net paper](https://arxiv.org/html/2601.00703v2) uses PSNR loss
for synthetic Bayer and Quad-Bayer experiments, while its real HDD experiments
use MSE. This supports testing a loss family, not importing its schedule, claiming
a reproduction or assuming a benefit on our physical Poisson/read-noise data.
No upstream code or weights are incorporated for this change.

```yaml
reconstruction_objective: image-log-mse-v1
```

For each image, the primary penalty is
`10 log10(max(mean(error²), 1e−10))`, then averaged over images. This is negative
PSNR with a100dB ceiling, evaluated in IEEE FP32. The control remains
`charbonnier-v1`, the backward-compatible default.

For synthetic Commons/native targets, this replaces the primary camera-linear
and rendered-RGB penalties. For real pairs, it replaces the measured-CFA and
coarse rendered penalties, using existing reference-validity masks and per-image
valid-sample counts. Images without valid samples contribute no value/gradient.
The separate auxiliary, gradient, highlight and optional sensor penalties retain
their original definitions and coefficients. Thus their **relative gradient
influence changes**; this is a loss-family test, not an isolated norm substitution
with matched gradient scales. Existing gradient clipping at1 remains fixed.
Loss values are negative and cannot be compared numerically to control losses.

The option consumes no RNG or model parameters and changes no inference code.
It propagates through ordinary and grouped mixed-domain batches. Checkpoints
serialize it; resume rejects a changed objective. Legacy checkpoints without
the field retain the original objective.

## Common data and training settings

The [expanded cache audit](commons-incoming-v5.md) and
[reviewed content quarantine](commons-content-overlap.md) precede admission.
The4× manifest retains84,867 train /2,303 validation /2,255 test sources with181
identified related-series/site training rows removed. It was not used by the
older trials. Both new arms use it; all held-out assignments remain fixed.
The standing GFX scene/siblings and protected-final scenes stay out of training.

V63's ancestor training used older manifests containing some identified related
series. New exclusions do not erase that ancestry or prove complete scene
independence. Review retains the previously frozen418/416-source sensitivities;
protected-final scoring stays closed. Comparisons to the V63 parent also change
data, optimizer state and horizon, so they cannot isolate the loss effect.

Both arms use B16/native256/BF16, LR1e−5, warmup100, seed51, fresh AdamW/EMA,
the same genuine frozen DINOv3 ConvNeXt-tiny and model tensors,4×→geometry/PSF→2×
augmentation, selected-domain loading, physical noise, flat palette and data
fractions. The original4,000-update horizon is retained when stopping at1,000.
Training destinations are inside a frozen hot-cache checkout to retain the
external SSD's500GiB reserve. Each worker has a24GiB CUDA allocator cap and a
one-hour limit. Only owned processes are controlled.

Configs: [V74 control](../configs/dino-convnext-v6-control-v74.yaml) and
[V75 log-MSE](../configs/dino-convnext-v6-logmse-v75.yaml). The controller uses
frozen copies with only output paths relocated inside its checkout. Model,
data, precision, LR, schedule and loss settings remain those of the templates.
First16 actual observations and all41 logged step/domain/noise/LR records must
match across arms. These checks do not independently hash every unlogged batch.

Parent SHA256:
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
Official DINO revision:
`10d30274b4d445111e2d5bf75ac93bbd94db274b`.

## Completed engineering checks

The focused CPU suite passes98 tests with one CUDA test skipped. Two additional
grouped-objective tests pass, comparing separate and joined mixed-domain loss
gradients. Independent scalar/NumPy arithmetic checks per-image log placement,
derivatives, unequal masks, empty references, exact targets and invalid masked
values. Explicit default losses remain byte-identical. Ruff passes changed code,
tests and the three new operators.

The genuine-parent CPU preflight runs four discarded B1/native64 FP32 updates
in control, log-MSE and2+2 resumed log-MSE arms. All four observation hashes match.
The interrupted result equals uninterrupted model/EMA/AdamW/Python/Torch/CUDA RNG,
step and best exactly, including an independent saved-state replay. Actual
DINO stays frozen. The91 model/91 EMA/89 optimizer states remain finite.

The CUDA preflight uses two fresh model/optimizer instances serially in one
process: six discarded updates each, B16/native256/BF16/workers4+2+2 and actual
Commons/native/paired data. All six observation hashes match. Genuine initial
EMA tensors match before the first forward; all89 trainable gradient tensors
are finite at every update; DINO stays unchanged and gradient-free. Independent
checkpoint replay finds89 changed model and89 changed EMA tensors per arm.
Peak CUDA allocation is7.20/7.02GB. These are engineering checks, not throughput
or restoration-quality measurements or deterministic CUDA restart evidence.

Observed pre-clip gradient norms are.057–2.545 for control and85.32–1007.79 for
log-MSE. The new family therefore clips every step in this small CUDA fixture.
This is an explicit experimental behavior, not a repaired-quality result.

The first training controller stopped before any model forward because its
frozen `writable_path` guard rejected the outer repository's hot-cache run path.
That plan/source/log/status remain unchanged. The corrected second plan moves
only its frozen output destinations inside the frozen checkout; both actual
path checks pass before launch. Its controller and CUDA child were verified
live after real optimizer updates began. Neither failure nor an observation
timeout triggers an automatic restart.

## Review before any further training

Evaluate both1k EMA checkpoints in fresh IEEE FP32 on all427 photographic
sources, seven noise/exposure conditions/four CFAs, the separate16 procedural
targets, four known/five unseen development camera scenes, and existing analytic,
hue and highlight panels. Compare matched control, own parent, RawNIND and
classical controls. Reuse old results only after matching protocol, coverage,
observations and sanity controls.

Reports must contain at least two native160px noisy/denoised/exact-synthetic-GT
triplets per new checkpoint, and standing GFX sky/building/foliage/fence contexts
with identical ROI/transforms. The separately captured ISO100 image remains a
qualitative reference, **not GT**. Review original pixels and retain full source,
checkpoint, conditioning and display metadata. Parent examples are already in
[the FP32 report](mature-cudnn-fullframe.md); they are not these unreviewed models.

The predeclared eligibility threshold for considering the remaining original4k
schedule is a log-MSE-minus-control full427 gain of at least.03dB with a positive
source-bootstrap95% interval, neither known nor unseen measured-CFA mean worse
by more than.05dB, and no visible new color/detail/highlight failure. Hue errors
must also be reported. Failing boundaries stop with negative evidence preserved.
There is no automatic continuation or model promotion. An eligible improved
candidate additionally needs full102MP FP32/RGB16 output and timing validation,
with cold and warmed scopes separate. Project SOTA, decisive real-photo
superiority and sub10s inference remain unproven.
