# Directional RAW residual and pre-clipping interval study

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

This is a new architecture/loss experiment, with no trained quality result yet.
The [completed V76/V77 study](camera-supervision-first1k-review.md) remains
closed at its failed original gate. Neither its checkpoints nor its optimizer
states initialize these arms. V43 was the reference for this experiment.

The implementation adds an opt-in `raw_directional_residual` around the mature
native-resolution RGB/DINO model. Four directional 33-sample averages and the
unfiltered observation supply five same-CFA-phase RAW candidates. Horizontal,
vertical and both diagonal filters span 65 native pixels; bilinear interpolation
then supplies the missing colors. The residual mixes candidate-minus-parent
predictions using the existing 67 RGB features and 16 local features derived
from noise-normalized measurement error, variance and explicit CFA labels.
The local network operates at packed resolution. The output heads start at
exact zero, preserving the entire parent output rather than resetting it to a
classical interpolation. The branch adds 25,800 parameters in eight tensors.

A separate signed color correction is gated by bilinearly interpolated observed
ADC-white indicators. At measured CFA positions, this correction is exactly zero
unless the observation reached ADC white. The directional mixture itself is not
restricted to censored samples. Learned, data-dependent filter choices are not
claimed to be unbiased or to preserve all scene frequencies. Directional support
fits inside the existing 48-native-pixel evaluation margin.

The [previous CPU gradient diagnostic](censored-highlight-gradients.md) found a
counterexample where display clipping and valid-sensor masking leave all color
correction gradients zero despite a remaining display error. The new opt-in
`reference_interval_weight` adds a Charbonnier penalty before display clipping.
Let `p = matrix @ (prediction * WB)` and `r` be the same transform of the existing
canonical reference-white target. The error is `p-r` for interior channels,
`min(p-1, 0)` for reference white and `max(p, 0)` for reference black, using the
diagnostic's fixed 1e-6 endpoint tolerance. This accepts a feasible white/black
interval without inventing an exact unobserved latent highlight. It does not
change inference or display/export transforms. Weight zero preserves the old
loss and gradients exactly. Nonzero weight requires sensor-valid supervision.
Paired RAW losses remain unchanged.

## Fixed training design

[V78 control](../configs/dino-convnext-directional-control-v78.yaml) and
[V79 interval](../configs/dino-convnext-directional-interval-v79.yaml) both use
the new branch, sensor-valid camera supervision and the genuine original20k
V63 EMA (`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`).
They differ only in interval weight: **0 versus 0.1**. Both start fresh
AdamW/EMA/RNG with seed51, batch16, native256, BF16, warmup100 and a complete
original **4,000-update** cosine schedule. Common LR is 1e-5; the new branch uses
20 times that scheduled rate (maximum 2e-4). This is 64,000 example draws per
arm, not complete coverage or convergence. Step1000/2000/3000 checkpoints are
engineering boundaries, with no early quality-based extension decision.

The cleaned84,867 Commons manifest, original validation targets, native128 and
paired32 manifests, .25/.25 native/paired fractions, physical noise, negative
read noise, camera/exposure draws, frozen official DINO and
[4× → geometry/PSF → area2 and selected-domain loading](training-pipeline.md)
remain fixed. No standing GFX scene or sibling enters training. Both arms sample
legacy/input-only batch hashes at the first16 and each25th update:176 records
per arm. All161 logged domains and common LRs must match. The initial common
EMA, zero heads, branch initialization and frozen DINO must match too.

The full budget is fixed before the new full quality review. No automatic
extension or promotion follows training. The worker stops on nonfinite values,
uses a 24GiB CUDA allocation cap, checks 40GiB available RAM and maintains
128GiB root / 500GiB external disk reserves. A bounded wall time is set after
the discarded actual-size execution check. Only owned child processes may be
terminated by this controller. Older stopped studies and their gates stay closed.

## Fixed review and eligibility

Evaluate both final EMAs and the genuine parent freshly with the same FP32
source-keyed observations: full427 photos, all seven conditions/four CFAs,
separate procedural16, known-four and unseen-five development measured-CFA
panels, and fixed418/416 source sensitivities. Preserve unfavorable canonical
camera-linear results with their target-convention caveat; do not substitute
physical training targets into evaluation. Ancestral related-series exposure
persists. Protected final scenes remain closed.

For either new arm to be eligible for a separate full-frame review:

- Known-four and unseen-five measured-CFA scene means must each improve at least
  .05dB over the genuine V63 parent, each with positive scene-bootstrap95% bounds.
- Full427 rendered PSNR must improve at least .05dB over that parent, with a
  positive source-bootstrap95% interval; SSIM may lose no more than .0001.
- Review the fixed hue/highlight and weak-texture analytic panels, at least two
  small native100% noisy/restored/exact-GT triplets per checkpoint, and cached
  DSCF3879/3880 sky/building/foliage/fence/highlight crops. Identical source/ROI
  and transforms, checkpoint hashes, noise and display exposure must be recorded.
  ISO100 is an independently demosaiced qualitative reference, not exact GT.
  No visible new color, detail or highlight failure is acceptable. Compare V43
  and the retained RawNIND output visibly as well as the genuine initializer.

The matched V79-minus-V78 comparison isolates interval supervision *within this
new architecture*. An interval-benefit claim additionally requires positive
full427 rendered-PSNR confidence bounds, known/unseen mean losses no greater
than .03dB each, and no visible new failure. It does not isolate the architecture
against the older V77 arm, which had a different update budget. Report all fixed
analytic/color groups, including unfavorable cases; do not pick new thresholds
or tune against the standing photos after seeing these results.

An eligible candidate still needs fresh full101.996MP FP32 restoration,
linear/sRGB16 export/quantizer verification, native-pixel visual review and
separate cold/warm timing. Passing this development gate cannot establish SOTA,
decisive real-photo superiority or the100MP/10s target. README sample pixels stay
at V43 until a stronger candidate passes review.

## Engineering evidence

The focused tests check independent FP64 filter samples, signed/above-white
constants, coherent carriers with independent noise, exact common initialization
and RNG, FP32/BF16 initial outputs and parent gradients, trainable new heads/local
features, CFA censorship, portable checkpoints, LR groups, grouped mixed losses,
and interval/restart guards. Synthetic learning fixtures establish execution and
gradients only. Genuine-parent CPU and CUDA receipts are recorded separately;
their updates and tiny validation runs are discarded and do not select recipes.
