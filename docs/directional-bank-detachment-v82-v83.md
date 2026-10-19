# V82/V83: fixed bank-input gradient comparison

This fresh comparison tests whether stopping the bank descriptor's gradient
into the RGB base reduces detail loss during fine-tuning. The
[fixed-weight gradient measurements](directional-bank-gradient-routing.md)
establish an isolatable route; they do not establish a quality benefit or the
cause of the historical ADC regression. Prior V78–V81 studies remain closed.

## Single intervention and original budgets

Both arms enable the same directional bank architecture. V82 keeps its input
connected; V83 sets `raw_directional_bank_detach_input: true`. This changes
backpropagation through the descriptor, preserving its forward values, bank
parameter learning, local directional path and RGB/DINO feature path. It does
not freeze the common network. No target, known frequency, ROI or method label
enters inference. Both arms have identical parameter counts and initial tensors.

Both start freshly from the genuine V63 original20k EMA, SHA256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`,
with fresh optimizer/EMA/RNG. Neither starts from a trained V80/V81 checkpoint.
Use seed51, B16/native256/BF16/channels-last, strict deterministic execution,
original **4,000-update** cosine horizon, warmup100, common maximum LR1e-5 and
directional LR multiplier20. Reference-interval weight remains0; sensor-valid
camera supervision and the complete loss remain fixed. Each arm draws64,000
examples. This is one matched training seed, not convergence or repeatability
evidence. The new connected arm is evaluated freshly even if it reproduces V81.

Both use the cleaned84,867 Commons manifest, native128/106 groups and paired32,
with.25 native/.25 paired fractions, unchanged exposure/noise/palette draws and
4×→geometry/PSF→area2. Only selected domains load data. The prepared private150
extension remains inactive. Standing GFX3879/3880 and all siblings remain outside
training. DINOv3 ConvNeXt-tiny remains frozen at revision
`10d30274b4d445111e2d5bf75ac93bbd94db274b`; official tensor SHA256 is
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.

The sole configured treatment difference is detachment; run paths differ too.
Require identical initial model/local/bank/DINO values, first outputs and raw
gradients (gradient hashing normalizes the sign of zero). Compare176 sampled
full/legacy/input observations,161 logged domains/LRs and final Python/CPU/CUDA
RNG. Retain1k/2k/3k engineering checkpoints. Full4k budgets are fixed before
quality review, without automatic extension or promotion. Nonfinite training
fails. Only this study's exact owned processes may be stopped for timeout.

Resource bounds are24GiB CUDA allocation,40GiB available RAM at worker launch,
24GB training RAM stop threshold,128GiB root/500GiB external free-space reserves
at launch, and10,800s per arm. The initial controller preflight runs six discarded
CPU B1/native64 updates per arm under the same original4k horizon and exercises
the final source/state/RNG comparison. The prior genuine-parent CUDA optimizer
preflight already covers both settings at B16/native256/BF16. These short checks
are engineering evidence and their validation monitors are not quality results.

## Predeclared review and decisions

Freshly evaluate both final EMAs and V63 in FP32 on all427 photographic sources,
seven conditions and four CFAs; procedural16; known-four/unseen-five development
measured-CFA panels; and418/416 source sensitivities. Retain canonical
camera-linear and highlight failures with the reference-white versus
sensor-valid target caveat. Do not replace evaluation targets or use protected
final scenes. Unknown related-series ancestry remains a limitation.

Eligibility for a later full-frame review preserves the prior requirements:

- Known-four and unseen-five measured-CFA scene means each improve at least
  .05dB over fresh V63, each with positive scene-bootstrap95% lower bounds.
- Full427 rendered PSNR improves at least.05dB over V63 with a positive
  source-bootstrap95% lower bound; SSIM loses no more than.0001.
- Native review shows no new color, detail or highlight failure.

A matched detachment benefit additionally requires a positive full427 PSNR
interval over the connected arm and known/unseen mean losses no greater than
.03dB each. To support the specific ADC-detail hypothesis, ADC-only
level.01/contrast.02/period4 signed gain must improve by at least.05 over
connected. Retain the previous high-noise weak-detail requirements too: gains
at level.01/contrast.1/period8 and level.18/contrast.02/period16 must each improve
by at least.05 over connected, with corresponding flat spatial-luma RMS no
greater than1.25×connected. Report all24 carrier/four flat configurations,
four CFAs/four draws, quadrature and noncarrier errors, and all hue/highlight
groups, including adverse groups. These are descriptive analytic observations,
not photographic or training-seed confidence intervals. Failure leaves this
study closed at its original4k budget, without promotion or automatic extension.

Each model performance report includes at least two small native100% noisy/
restored/exact-GT triplets, identical source/ROI/transforms, checkpoint SHA,
noise conditioning and display exposure. Compare actual V63, V43 and RawNIND
alongside both arms. View cached GFX sky/building/foliage/chain-link-fence/lights;
label ISO100 as an independent qualitative reference with aperture/motion
differences. Never resize crop pixels or score that reference as pixelwise GT.
Keep the representative working README crops until a stronger model is verified.

An eligible model still needs its own complete101.996MP run, linear/sRGB16
export and quantizer checks, native visual inspection and cold/warm timing.
This development comparison alone cannot establish SOTA, broad real superiority
or the100MP/10s goal. V43 remains the working reference during the experiment.
