# Fixed V90/V91 late RGB refinement comparison

This experiment tests spatial semantic access in a learned RGB refinement
head. V90 receives spatially pooled DINO prompts; V91 receives their spatial
fields. Both start from genuine V63 original20k EMA and use the same new
100,547-parameter head. No quality improvement or promotion is assumed.

## Motivation and isolated intervention

[PixIE, July2026 v3](https://arxiv.org/html/2605.23531v3) separates denoising
from foundation-guided pixel refinement and restricts semantic propagation.
It studies RGB low-light enhancement, not noisy Bayer reconstruction. Our
inference is to test a separate late RGB stage after the
[fixed spectral innovation failed](spectral-innovation-split.md). This is an
independent design, not a reproduction or transfer of published scores. No
upstream code, weights or training data are incorporated from PixIE.

The mature model's existing earlier DINO guidance remains in both arms. This
is not a semantics-free initial denoiser or an ablation of all early guidance.
The new head operates after the common RGB trunk, on normalized stabilized
coordinates, before the unchanged physical inverse transform. It learns three
RGB corrections directly; there is no fixed CFA/Malvar innovation, sample
projection, spectral mask, target-dependent forward or extra DINO encoding.

Head inputs are the native64 decoder features plus3 normalized predicted RGB
channels and the existing21 physical CFA/camera/noise-conditioning channels.
A1×1 projection produces32 channels. Two residual neighborhood blocks each
sum depthwise3×3/5×5 convolutions, apply GELU and a1×1 mix. A zero-initialized
3×3 RGB output adds a residual to the normalized prediction.

The four already computed frozen ConvNeXt stages each feed a zero-initialized
1×1 projection to64 scale/shift channels. V90 averages each projected field
over its spatial grid and broadcasts that mean; V91 retains its spatial
field. Bilinear upsampling uses the actual4/8/16/32 strides in the padded32px
coordinate system, then crops the tail. The four fields are averaged and apply
`hidden*(1+scale)+shift` before the neighborhood blocks. Both modes have the
same tensors, parameter count, head optimizer and original DINO input. This
isolates spatial prompt access, not total foundation-model benefit or parameter
efficiency. The original frozen encoder executes once per actual forward.

Head construction preserves the common CPU RNG. Both mode states are identical
at initialization; zero modulation and RGB output preserve parent values and
common gradients. Output weights can learn immediately, with semantic
projections learning after that output becomes nonzero. Frozen DINO features
are detached; its weights remain eval/frozen and excluded from EMA. The optional
model setting defaults to `none`, preserving legacy checkpoint behavior.

## Common data and training recipe

Use the reviewed88,508-source Commons4× training manifest, native128 captures
in106 groups and paired32 scenes. Validation/test memberships remain fixed.
The later private150/public18 extensions remain inactive. Cached GFX3879/3880
and their entire series remain excluded. No original personal capture is
modified or read for this experiment's prepared training data.

Native256/B16, seed55, BF16/channels-last, deterministic execution, original
official frozen DINOv3 ConvNeXt-Tiny revision
`10d30274b4d445111e2d5bf75ac93bbd94db274b`, sensor-valid physical targets,
Charbonnier objectives, .25native/.25paired fractions, existing physical
Poisson/read/ADC synthesis and negative read noise, flat/procedural palette,
4×→geometry/PSF→area2, LR1e-5/warmup100/cosine4000/10%floor. Both head groups
use the same20× LR multiplier. Each original4000 arm draws64,000 examples.
Initialize from V63 original20k EMA checkpoint SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.

No new loss, supervision target, noise recipe, context extent, batch size or
foundation checkpoint differs between arms. Both include the previously
verified inverse/physical-feature implementation cleanups. The historical V88
control is not substituted for a fresh matched global-prompt arm.

Record the actual source/forward/loss fingerprints at steps1–16 and every25;
require equal domains, common LRs, source archives and final Python/CPU/CUDA
RNG. Require identical common initial state, actual first-forward parent replay
and initial global/spatial gradient fingerprints, canonicalizing signed zero
to match tensor equality. These logged observations do not replay every
unrecorded sample. Check all model/EMA/AdamW finite states and counters; retain
original1000/4000 states. Routine validation cannot choose, shorten, extend or
promote either arm.

## Engineering and resource bounds

Before full training, require CPU unit/regression checks for zero initialization,
common gradients/RNG, detached/frozen DINO, one encoder pass, global-versus-
spatial access, batch independence, padded-coordinate cropping, mixed noise
families, exact LR groups and portable reload with missing-state rejection.
Then require discarded genuine-weight CPU/B1/native64/FP32 and
CUDA/B16/native256/BF16 mixed-domain16-update preflights, each including the
fresh-process uninterrupted versus8+8 full model/EMA/AdamW/RNG comparison.
All preflights retain the original4000 LR horizon and are not quality training.

Freeze all sources/configs/inputs before each phase; require their agreement
across CPU, CUDA and full runs. Run one owned training arm at a time, with48GiB
available for60s before full launch,24GiB CUDA quota, root64GiB/external500GiB
reserves and14,400s per-arm/resource-wait bounds. Stop only the exact owned
worker if remaining RAM falls below24GiB or a disk/time bound fails. Preserve
failed artifacts/checkpoints; no automatic retry, schedule extension or change
to another project's processes.

## Required quality review

Only original4000 endpoints enter the final comparison. Fresh FP32 evaluation
uses the unchanged known4/unseen5/full427 photographic and16 procedural sources,
all seven conditions/four CFAs, canonical camera-linear scores,418/416-source
sensitivities, analytic/ADC/hue/highlight panels and V43/RawNIND references.
All fixed native boards must actually be viewed before numerical decisions.
Keep unfavorable sources/conditions. AHD and GFX ISO100 are not exact RGB GT.

A spatial-access benefit requires a positive lower95% source-bootstrap photo
PSNR bound versus global, known/unseen losses at most.03dB, photo-SSIM
loss≤.0001 and no new visible failure. A weak-detail benefit requires at
least+.05 signed gain on both existing high-noise carriers, flat spatial-luma
RMS at most1.25×global, and no individual ADC gain loss greater than.05 across
all192 layout/draw slots. Retain all12 ADC group means and distinguish
deterministic ADC draw labels from independent observations.

Each endpoint independently requires at least+.05dB over fresh V63 on photo,
known4 and unseen5 with positive95% lower bounds and photo-SSIM loss≤.0001,
plus complete native review before full-frame eligibility. One seed/source
bootstrap does not measure training-repeat uncertainty; passing these gates
does not establish SOTA or automatic promotion.

Reports must include at least two native160 noisy/restored/exact-synthetic-GT
triplets per endpoint, identical source/ROI/noise/color/exposure, complete
checkpoint hashes and the standing GFX sky/building/foliage/fence plus sign/
platform views. Never resize crop pixels, fit display exposure by method or
score GFX against its independent ISO100 reference. Keep a representative set
in the top README only after justified promotion. Protected-final scenes remain
closed; no new full102MP export or speed claim follows from engineering checks.
