# Camera-target convention audit and matched V76/V77 trial

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

A noiseless analytical audit finds incompatible camera-space meanings in the
canonical highlight target and a constant-preserving RAW head. This motivates
a default-off training mode, `camera_supervision: sensor-valid-v1`, and a fresh
matched control. It is not evidence that a newly trained model is better.

The [completed full review and native GT crops](camera-supervision-first1k-review.md)
find+.16011dB rendered photo PSNR,−.02714dB known4 and+.08098dB unseen5 at1k.
Known4 fails the original continuation screen, so neither arm extends or promotes.
All67 native triplets/111 cells, full427/color/GFX/analytic/source-sensitivity
and independent numerical reviews are complete. Weak texture remains missing.

## Concrete conflict

The [executed audit](results/camera-target-convention-audit-v1.json) uses the
actual `AdaptiveRawKernel`, three constant RGB scenes and all four CFA phases.
It loads no trained checkpoint or DINO weights and uses no CUDA. On the exposed
linear-sRGB color [1.4,.4,.2], WB [2,1,1.5] and the fixed protocol camera matrix,
the physical camera RGB is [.64499998,.43999997,.17999996]: every sensor channel
is unclipped. The existing reference-white target instead becomes
[.46500000,.41999999,.16666664] because it clips in linear sRGB before converting
back to camera RGB.

The centered RAW head preserves the physical constant color. Canonical target
MSE is .01099258 with **exactly zero** coefficient/feature gradients; physical
measured-CFA MSE is zero. A diagnostic reference-white projection reduces
canonical MSE to approximately 3e-16 while creating .00834444 physical CFA MSE.
Therefore, appending that projection to a physical RAW head would exchange one
error for another. This audit does not isolate the causes of prior training
failures or prove the same limitation for the mature V63 RGB backbone.

The first execution passed numerically but had a Ruff closure warning. Binding
the loop variables explicitly produced a clean second execution with identical
cases. Both originals remain preserved, and the public registry identifies the
actual archived second-execution sources. Existing benchmark targets remain
unchanged.

## Optional training behavior

`reference-white-v1` remains the default. In `sensor-valid-v1`, Commons and
native-RAW degradation retain the existing exposed, latent camera RGB as
`sensor_target`. This requires no extra image loading, augmentation or random
draw. Primary camera reconstruction and auxiliary CFA supervision use that
physical target only where its value is in [0,.98). Validity depends on the
target, not the prediction. Invalid elements are masked before squaring;
empty masks contribute zero with finite zero gradients.

Rendered reconstruction, rendered gradients, highlight color terms and their
coefficients retain the canonical reference-white target. Paired-RAW loss is
unchanged. Optional normalized/multiscale camera losses use the physical target;
both weights are zero in this experiment. The mode requires
`reconstruct_highlights: true`, is recorded in checkpoints, and cannot change
during full-state resume. Historical checkpoints missing the field mean the
default reference-white convention. No network architecture, forward graph,
evaluation target, RAW projection or output calibration changes.

The independent archived-default audit compares actual pre-change source to
current code: 12 Commons/native observations have exact tensors and post-noise
RNG; 48 loss/part/prediction-gradient comparisons pass across both objective
families and optional physical auxiliary weights. Fourteen forward/dependency
files are byte-identical. This CPU result does not claim CUDA trajectory parity.

All 64 focused tests pass in 6.62s, and Ruff passes. Tests cover target retention without RNG changes, unchanged rendered
terms, empty/invalid masks, grouped mixed-domain gradients, and exact interrupted
resume. The [engineering registry](results/camera-supervision-engineering-v1.json)
records the actual archived replay, genuine-parent CPU exact4-step/2+2 restart,
and six discarded GPU updates per mode at B16/native256 BF16. Both GPU modes
have 89 finite gradients at every update, finite91/91/89 model/EMA/Adam states,
identical six legacy/input observations, exact parent EMA initialization and
unchanged official DINO hash. Peak CUDA allocation is 6.706/6.573GiB; this short
engineering fixture is not a throughput comparison. No quality claim follows.
An additional41 source-sensitivity/native-board tests pass. The
[publication validation](results/camera-supervision-validation-v1.json) verifies
source/PNG/link bindings and replays81 existing V74/V75 sensitivity comparisons
exactly through the new report-status contract. That replay supplies no V76/V77
quality results.

## Matched first boundary and predeclared review

[V76 control](../configs/dino-convnext-camera-control-v76.yaml) and
[V77 sensor-valid](../configs/dino-convnext-camera-sensor-valid-v77.yaml) start
fresh AdamW/EMA/RNG from the same genuine original20k V63 EMA, SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
The sole policy difference is `camera_supervision`. Both use Charbonnier,
batch16/native256/BF16, LR1e-5, seed51, warmup100 and the original4000-step
schedule, stopping at1000. This is 16,000 examples per arm, not complete coverage
of the 84,867-source corpus or convergence. The failed V74/V75 objective study
remains closed at its own original gate.

Both arms use the same cleaned Commons4× manifest, native128/106 groups and
paired32, with .25 native/.25 paired fractions. The requested
[4× → geometry/PSF → area2, selected-domain loading and measured batch choice](training-pipeline.md)
remain fixed. Actual legacy batch hashes (excluding only the newly retained
target) and input-only hashes are sampled at the first16 and each25th update:
56 observations per arm. Full batch hashes intentionally differ when the new
field exists; those hashes must not be described as identical. All41 logged
domains and learning rates must match. Genuine parent initialization, frozen
official DINO, finite checkpoint states, frozen source/data/config hashes and
resource guards are checked by the owned controller.

The [launch receipt](results/camera-supervision-v76-v77-launch-v1.json) identifies
the frozen211-file corrected checkout and actual controller/child identities.
The first checkout omitted the three required third-party license files and
stopped during provenance capture before model load or any update. Its plan,
source, status and log remain unchanged. The corrected plan adds those exact
license files and relocates outputs; package/worker/review-criteria bytes are
identical. This is an explicit diagnosed correction, not an automatic retry.
The [owned review queue](results/camera-supervision-review-queue-v1.json) waits
for that exact controller and its children to exit successfully, then checks
both complete boundaries before running the fixed FP32 photo/camera/color/native
panels and independent source sensitivities. Waiting is not a quality result;
manual native review and numerical closure remain required afterward.

Before any new quality results, continuation eligibility is fixed as follows:

- Both known-four and unseen-five development measured-CFA scene means must
  improve by at least .05dB over matched V76, each with a positive scene-bootstrap
  95% interval.
- Original full427 rendered PSNR must lose no more than .03dB and rendered SSIM
  no more than .0001. Report the entire original seven-condition/four-CFA panel,
  separate procedural results and fixed418/416 source sensitivities.
- Review the existing hue/highlight/analytic panels and at least two exact-GT
  native crop triplets per checkpoint. Review cached GFX sky, building, foliage,
  fence and highlight contexts with identical coordinates/transforms and honest
  independent-reference labels. No visible new color, detail or highlight failure.

Passing only permits considering the remaining original schedule. There is no
automatic continuation or promotion, and no tuning against selected photos.
An eligible improved candidate still needs actual full101.996MP FP32 restoration,
linear/sRGB16 quantizer checks and separate cold/warm timing. Protected final
scenes remain closed. Camera-linear scores against the unchanged canonical
benchmark target retain the convention caveat; report them without relabeling
the target or substituting physical training targets into evaluation.

Own-parent differences also include data, fresh optimizer and schedule. Related
capture-series ancestry is not removed by the new quarantine. A successful
first boundary alone cannot establish SOTA, decisive real-photo superiority or
the100MP/10s target. V43 was the reference for this experiment and its README crops stay.
