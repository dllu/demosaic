# Directional candidate context: fixed V80/V81 experiment

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

This fresh architecture comparison tests whether exposing averaged measurements
to the directional mixing network improves weak-detail recovery. The completed
V78/V79 interval study remains closed. Neither its trained checkpoints nor its
optimizer states initialize these arms. V43 was the reference for this experiment.

## Intervention

The existing directional head computes five same-CFA-phase candidates: the raw
observation and four 33-sample line averages. Its weights see local RAW residuals
and the mature RGB/DINO features, without direct access to those averages.

`raw_directional_bank_context: true` additionally exposes all five packed
candidate-minus-parent residuals, divided by the original measured-sample noise
scale and clipped to ±8. The original scale is a feature normalization, not a
calibrated uncertainty for correlated candidate/parent errors. A packed two-layer
3×3 network (20→32→64), GELU and pixel shuffle supplies 16 native features.
A zero-initialized 1×1 head adds 15 corrections to the existing mixture logits
before tanh. All candidates are reused; averaging is computed once per direction.
The censored-color head is unchanged. Targets, known frequencies or ROI labels
never enter inference. No unbiasedness or universal frequency-preservation claim.

The option adds 24,543 parameters in six tensors. Independent initialization
preserves common global RNG and weights. The zero logit head preserves both a
fresh parent's and a trained directional parent's predictions and common raw
gradients. Global gradient clipping includes the new trainable parameters, so
the clipped common gradients can differ once the new head receives a gradient.
The option defaults off and old checkpoint configurations retain that behavior.

## Fixed training

V80 control disables the new context; V81 enables it. Both initialize the genuine
original20k V63 EMA, SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`,
with fresh optimizer/EMA/RNG and seed51. Both use strict deterministic execution,
B16/native256/BF16, channels-last, the original complete **4,000-update** cosine
horizon, warmup100, common maximum LR1e-5 and directional LR multiplier20.
Interval weight stays zero and camera supervision stays sensor-valid. Each arm
uses64,000 example draws; that is not convergence or complete corpus coverage.

The sole configured intervention is bank context. Common data, source indices,
noise, exposure/camera draws, official frozen DINOv3 ConvNeXt-tiny revision
`10d30274b4d445111e2d5bf75ac93bbd94db274b`, losses, rendering and geometry stay fixed.
Use the cleaned84,867 Commons manifest, native128/106 groups and paired32 groups,
with .25 native/.25 paired fractions. The prepared private150 extension stays
inactive to isolate architecture. Geometry/PSF operates between4× and final2×
reductions; only selected domains load training batches. The standing GFX scene
and all siblings stay excluded.

Both arms sample legacy/input batch identities at the first16 and every25th
update (176 records), log161 shared domains/LRs, and verify final RNG identity.
Checkpoints at1k/2k/3k are engineering boundaries. The complete4k budget is fixed
before quality review; no automatic extension or promotion follows. Nonfinite
training fails. Resource limits are24GiB CUDA,40GiB available RAM at launch,
128GiB root and500GiB external free-space reserves, with10,800s per arm. Only
the exact owned worker group may be terminated for timeout.

## Fixed review

Evaluate both final EMAs and the genuine parent freshly in FP32 on full427
photos/all seven conditions/four CFAs, procedural16, known-four and unseen-five
development measured-CFA panels, and418/416 source sensitivities. Preserve the
canonical camera-linear/highlight failures and their target-convention caveat;
do not substitute training targets into evaluation. Ancestral related-series
exposure remains a limitation. Protected-final scenes remain closed.

Eligibility for a separate full-frame review retains the prior requirements:

- Known-four and unseen-five measured-CFA scene means each improve at least
  .05dB over the genuine V63 parent, each with positive scene-bootstrap95% bounds.
- Full427 rendered PSNR improves at least .05dB over that parent with positive
  source-bootstrap95% bounds; SSIM loses no more than .0001.
- No visible new color, detail or highlight failure in the fixed native review.

A matched bank-context benefit additionally requires a positive full427 PSNR
interval over control and known/unseen mean losses no greater than .03dB each.
For the stated weak-detail hypothesis, each of the two fixed high-noise carriers
(level.01/contrast.10/period8; level.18/contrast.02/period16) must improve mean
signed in-phase gain by at least .05 over control. Report all four-CFA/four-draw
cases, quadrature and noncarrier error; these are descriptive analytic cases,
not photographic confidence intervals. At each corresponding flat level,
high-noise spatial-luma RMS must not exceed1.25 times control. Report the complete
fixed carrier/flat and hue/highlight panels, including adverse groups.

Every improved-model report includes at least two small native100% triplets of
noisy/restored/exact GT with identical coordinates/transforms, source equation
or identity, checkpoint hash, noise conditioning and display exposure. Review
cached DSCF3879/3880 sky, buildings, foliage, fence and saturated lights; label
ISO100 as an independent qualitative reference, with aperture/motion differences.
Compare the actual parent, V43 and retained RawNIND visibly. Keep all crop pixels
unresized. No tuning against standing photos or new thresholds after results.

An eligible candidate still needs its own full101.996MP FP32 run, linear/sRGB16
export/quantizer checks, native review and cold/warm timing. These development
criteria do not prove SOTA, broad real superiority or100MP/10s. README model
pixels stay at V43 until a stronger candidate passes review.
