# V150 matched loss-floor trial

Recorded: 2026-11-03T15:03:40-08:00 (America/Los_Angeles).

Started a matched2/16 DN loss-floor trial after the completed supervision
allocation probes showed large ADC pressure. Both heads retain the identical
31,409-parameter native matrix architecture and twelve initial tensors. Only
the per-image RGB standard-deviation floor and per-phase spectral variance floor
change together. Existing source/geometry/domain weights, pre-gate spectral
objective, physical inputs,1k horizon, LR/schedule/clipping and EMA remain fixed.
Adopt all1,000 V148 batches/4,000 old observations and parents, with no new
training noise or parent/DINO call. No neural or inference source changed.

Added8 old exact synthetic photographic ADC observations (bark/fur across4CFAs)
and16 new analytic native512 sloped-plane ADC observations, all held out from
training. Both photographic source IDs retain the original train-disjointness
audit, matching train manifests and absence from actual cached training metadata.
Two older approximate binned camera references were deliberately not adopted.
Independent long-double checks cover4,194,304 new packed ADC values, maximum
FP32 difference .001953 DN16. Direct quantization draws no stochastic noise.

Cached24 new V143/DINO parent contexts before head training. All24 calls finish
with model/backbone hashes and CPU/CUDA RNG unchanged, peak .99 GiB CUDA. Only
cached repo/external inputs are read; originals/protected siblings remain read
only and excluded, with no RAW/dataz access. These controls are never fed to
training. All4 final raw/EMA endpoints cover822 cases and3,288 component calls.
The72 fixed native figures include24 repeated triplets and both standing real
scenes, mesh priors/windows/JPEGs. Real ISO100/AHD/JPEG references remain
qualitative, not exactGT; actual blank/DC/spatial and quiet errors remain in review.

All8 new objective tests passed in1.10s over4CFAs and ADC/high-noise cases.
Helper2 DN exactly matches the old coefficient value/gradient;16 DN leaves the
high-noise value/gradient unchanged and scales ADC spectral gradient by1/64.
Compatibility preserves28 trained old/current/archive cases exactly (56 actual
forward-function evaluations). Both fresh heads pass CUDA10 each with genuine
8+2 restoration, all12 nonzero finite gradients and4.07 GiB peak. Production
starts fresh afterward, with no worker replacement/restart.

The reporting preflight passes64 parent cases (32 mixed+8 meshes+24 ADC),280
independent scalar checks, maximum1.24e-13 and no CUDA initialization/NN/noise
calls. Its first harness used the original review-module name instead of the
frozen file path and stopped during imports. Preserve that source/error and
load the actual frozen review file; no reporter/model/input/worker changes.

Checkpoint250 contains24 finite Adam states and finite raw/EMA weights in both
heads. The native control's raw/EMA/Adam state matches V149 exactly. Preparation
publication records an active423-row complete native loss/gradient/LR trace
prefix, exact against V149, with both controllers and the training worker
verified live. All13 receipt copies preserve their original bytes. This is
readiness and active-state evidence, not quality improvement. The final1k
states, every fixed endpoint, independent scores and actual native viewing are
still pending. The broader fine-detail/clean-sky goal remains active and unmet.

[Protocol/current status](../docs/objective-floor-training.md) ·
[Preparation evidence](../docs/results/v150-objective-floor-preparation-v1.json).

Both fresh heads subsequently completed1,000 updates. The final CPU state audit
passes all24 finite Adam states and exact native control loss/gradient/LR trace,
raw/EMA/Adam reproduction versus V148/V149. The four fixed endpoints complete
all822 cases (3,288 component calls), with parent/model/RNG bindings preserved
and no extra parent/DINO/noise calls. Independent full replay verifies all1,596
retained control predictions exact; the24 new ADC controls have no older head
archive. The source helpers/inputs/scientific workers were never replaced.

Independent metrics pass40,210 scalar checks and476 Decimal reductions, maximum
4.55e-13. Renderer/display/PNG checks cover32,332,800 RGB channels. Actually viewed
all72 primary figures at original detail in18 unscaled sheets, with notes saved
after each group. All10 primary process owners, including the ADC parent worker,
are terminal; no experiment jobs remain. Published14 byte-exact final receipt
copies and72 native PNGs. The active423-row snapshot and all earlier evidence
remain unchanged.

The16 DN loss improves mesh response3.67–5.30% over native control, but it remains
4.26–4.54% below V143. Actual blank/empty errors move closer to parent but remain
higher. No useful new fine cab wires, crossing family or noisy feather/moth/grass/
bark detail appears. Mean mesh support stays near.16 while coefficient correction
RMS roughly halves; this is a smaller proposal, not proof of spatial selectivity.

There are useful narrow gains: native512 noisy-flat full RMS improves about
.045–.047% versus V143, rather than regressing as the2 DN control does. Full spatial
error also improves, while block32 changes remain tiny/mixed and colored mottle
is still visible. Both noisy dark-photo full errors improve slightly, without
reversing any noisy photographic band regression. Strong-edge whole RMS improves
.276–.370% versus V143, while exact quiet errors remain higher, albeit less than
the2 DN control. Native sky stays close to parent.

The new ADC photo controls uncover measured gains for both late heads: floor16
full RMS improves3.057–3.058%, versus2.835% native control; both improve band error
versus V143, but2 DN has the better ADC band. Fine bark/fur remains present, with
small visible changes under diagnostic40×. Sloped ADC full/spatial errors also
improve about2% versus V143, less than2 DN, while coarse block32 RMS rises about
28%. Worst DC improves slightly. Central crop-only reporting would hide the
wider-field coarse regression. All48 older constant ADC cases stay exact parent.

The final routing audit binds all1,000 rows per arm. ADC clipping falls35→4 out
of118; none of882 noisy steps exceed1. Median ADC norm becomes .298018→.018555;
noisy norm also falls .017676→.006884. ADC still provides95.162% of a cap-at1
squared-norm proxy, which does not measure Adam influence or explain quality
causally. First two arm traces match; first difference is the ADC batch at step3.

Use the tested16 DN objective for the next noise-focused late-head control,
retaining2 DN as the ADC band/coarse-flat comparator. This adopts the actual
limited gains rather than freezing the older harmful objective. No inference
integration or general recommendation change. Further isolation of ADC
supervision remains justified; relative-phase evidence and aggregation are also
open estimator questions. The high-ISO fine-detail/clean-sky objective remains
active and unmet. README now shows two native ADC gain triplets alongside the
standing main/green-mesh comparisons; noisy organic weaknesses remain linked.

[Final evidence](../docs/results/v150-objective-floor-final-v1.json) ·
[Final state audit](../docs/results/v150-objective-floor-training-state-v1.json) ·
[Complete training routing](../docs/results/v150-objective-floor-routing-v1.json).

