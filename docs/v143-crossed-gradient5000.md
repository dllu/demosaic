# V143: completed5k with crossed-line data and smaller gradient smoothing

**The original5,000-update run and all three fixed reviews are complete.**
The [final report](v143-final5000-quality.md) gains0.26493dB faint ADC PSNR and
4.64% lower noisy-flat spatial RMS overV120, with coarse/ADC costs and no clear
new real-mesh recovery from training alone. The result is useful for further
faint-detail work; V120 remains the general recommendation.

[Recipe](../configs/quality-v120-crossed-gradient5000-v143.yaml) ·
[Setup checks](results/v143-crossed-gradient5000-setup-v1.json) ·
[Actual final boundary](results/v143-final5000-boundary-v1.json) ·
[Complete quality receipt](results/v143-final5000-quality-v2.json).

## Candidate and comparison scope

Fresh V12020k EMA initialization;90,782 photos/27 reviewed regions,seed70,
50% reviewed quota,native256/B16/BF16,zero optical PSF,LR1e−5,warmup100.
V142's crossed-line/empty sources occupy.10 of the existing.15 weak quota,
with half absent. Pixel Charbonnier epsilon stays.0003; gradient-error epsilon
becomes.00003. Loss coefficients and paired objective stay fixed. The official
DINOv3 ConvNeXt-Small encoder remains frozen.

The cosine horizon is5,000, with immutable1k/2.5k captures from the same worker.
Compared with V1421k, both gradient smoothing and LR horizon change. This is
not an isolated or equal-budget loss comparison. CPU128/B1 and CUDA256/B16
checks execute16 fresh+2 resumed updates, match all18 V142 clean/noisy inputs
and4,259,840 initial output values, and reject inherited/invalid epsilon before
constructing a resumed model. Production matches its genuine CUDA prefix.

## Completed fixed reviews

Each1k/2.5k/5k point uses the same102 IEEE-FP32 observations:64 shadow,16
ordinary,16 faint ADC,four main GFX512 contexts and two extra-mesh768 contexts.
V120/V129/V141/V142 predictions are reused, preserving source masks, ROIs,
CFAs, noise draws and displays. Both protected GFX pairs, foliage/fence/sky/
building, both mesh priors and camera JPEGs remain included. Independent
ISO100/AHD/JPEG and approximate binned references retain **not exactGT** roles.

Each point also uses48 analytic uniform fields, with V120/V142 controls and
fixed two-window/ten-peak mesh-power diagnostics. Each reuses504 control
predictions with no new review noise, RAW decodes or control-model calls.
Actual native viewing follows independent numeric/pixel audits, including at
least two native noisy/restored/exact-synthetic-GT triplets.

- [1k progress](v143-progress1000-quality.md): faint regression and no mesh gain.
- [2.5k progress](v143-progress2500-quality.md): faint recovery nearV120.
- [Completed5k](v143-final5000-quality.md): useful faint/shadow/noisy-flat gains,
  with explicit coarse/ADC costs and real mesh still weak.

Binding verifies original worker identity, step/horizon/lineage, finite91
model/EMA tensors and89 Adam states, exact69 trained modules and every first
1,000 input hash against V142. V142 has no later inputs to match. The78-test
review suite covers contracts, retained analyses and adoption identity/deadline
rejection. A [legacy-default replay](results/v143-review-backcompat-v1.json)
checked85 frozen files and normalized primary/faint plans against archived
preparer bytes; original receipts and operators remain preserved.

## Preserved failures and genuine completion

The original1k flat collector saved48 predictions but timed out before final
state/RNG verification. Those outputs remain unverified. A separately recorded
one-call probe and48-call one-thread recollection passed all complete checks;
only the latter outputs enter flat quality. [Recovery evidence](results/v143-progress1000-flat-recovery-v1.json)
records small FP32 differences without claiming bitwise parity or root cause.
This adds49 calls: actual three-point total499 instead of the original450.

The original training controller later disappeared; its tool session returned143,
with cause unestablished. The same original worker remained alive. A separate
[supervisor](results/v143-original-worker-adoption-v1.json) adopted that exact
PID/creation time, frozen command/plan and original8h deadline. No training
restart, checkpoint resume, budget reset or original-status rewrite occurred.
The worker retained its12GiB CUDA cap and32GB RAM floor. Its genuine5k receipt
and dead owner were verified before endpoint inference.

The original stale status and both failed review watchers remain preserved.
The completed endpoint supervisor's status is retained at
`.cache/quality-20261102/V143-fixed-reviews-v4/status.json`.
Canonical read-only checkpoint:
`/mnt/external/demosaic/models/v143-final5000.pt`, SHA256
`96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`.

The [first-batch loss diagnostic](crossed-line-loss-gradients.md) and
[procedural response test](crossed-line-response.md) are separate measurements;
neither attributes final quality. The [local phase-aware correction](local-phase-harmonic-patch.md) now tests
V143 with stronger mesh and reduced but remaining localization cost. It is not
part of the checkpoint; tested96-photo/48-flat parent values are unchanged.
Full427-photo, camera/color, full-frame and speed results forV143 remain open.
