# Full quality qualification of mature hidden FP16

**Execution stopped before the full quality suite.** The first frozen launch
passed its genuine CPU proof, then failed the fixed matching-policy CUDA
preflight on the first V43/GFX hidden-FP16 prediction. Its four crops had maximum
differences `.64794/15.74976/4.43939/10.92171` DN16 and RMS
`.05791/.21689/.06818/.09859` DN16 against the saved hidden-FP16 pilot output.
Three maximum differences exceed the prospective1DN16 limit. No known/unseen,
full-photo, analytic, color-grid or full-frame continuation ran. This is an
execution mismatch, not a full-population quality result.

The stopped plan is
`.cache/benchmarks/mature-hidden-FP16-full-quality-v1/plan.json`, SHA256
`aa076e39113bec7b24a8f1c5816f747a069cfcb7e04842d9cd0c0d91fb428da3`.
Both exact owners exited. All frozen inputs, source, checkpoint snapshots,
CPU receipt and failure log remain intact. The CPU proof ran51 actual forwards
per model:50 paired-runner forwards with50 boundary/DINO calls, plus one
ordinary direct FP32 control. Both controls match the runner byte for byte;
model/config/parameter/RNG checks pass and CUDA stayed uninitialized.

A separately frozen four-arm diagnostic on only the failed V43 B4 GFX input
compares fresh processes using the paired sequence, the pilot's original
three-policy warmup history, cuDNN benchmarking disabled, and loading under the
pilot's outer inference-mode scope. All34 forwards/136 policy observations
complete, saving every prediction before deriving differences. All actual model,
DINO, config, parameter, input, boundary-call and RNG checks pass; the controller
and all children exit successfully. Each within-process repeat is byte-exact.

| Fresh-process arm | FP32 max DN16 vs pilot | Hidden-FP16 max DN16 vs pilot | Pilot parity |
| --- | ---: | ---: | --- |
| Paired, autotuned |0|15.74976|Fail|
| Original three-policy warmup, autotuned |.04687|15.74976|Fail|
| Paired, cuDNN benchmark disabled |.05859|15.34742|Fail|
| Original warmup and outer inference-mode loading |0|15.74976|Fail|

The ordinary-FP16 captures in the two history arms also differ from their
matching pilot output by15.17164DN16 maximum. The diagnostic does not isolate
the cause. Model source modules and precision helpers are byte-identical between
the original pilot and qualification bundles; actual learned/DINO hashes match.
Within-process repeatability does not establish parity with the saved pilot.

The [independent NumPy64 audit](results/mature-precision-execution-independent-audit-v1.json)
recomputes all106,954,752 saved RGB values and every recorded physical difference
and byte identity, with zero scalar disagreement. The
[complete stopped-run result](results/mature-hidden-FP16-full-quality-preflight-v1.json)
binds original checkpoints, both freezes, CPU proof, unit tests, failure snapshots,
all four arm summaries and the executed independent auditor.

No parity/quality limit changes and no qualification retry or new speed claim
follow. The original failed worker saved its successful FP32 array but raised
before saving the unfavorable hidden-FP16 array; its traceback preserves all
four crop differences. The diagnostic saves all outputs. The checkout preflight
writer now also preserves an unfavorable prediction and its labeled differences
before raising; this does not alter the frozen run. No GPU end-state certificate
is claimed for the failed original worker, which did not reach that receipt.

The remaining text records the prospective protocol frozen before that launch.

The completed [finite pilot](mature-mixed-precision-pilot-review.md) selects
hidden FP16 on the original V43/V63 checkpoints: every fixed screen passes,
with resident B4/native512 median ratios4.250×/4.060×. This separate study
tests the broader quality scope before any production integration or new
100MP speed claim. Neither weights nor training recipes change.

Use a fresh source-frozen bundle, original byte-exact checkpoint copies and
the same physical implementation. Compare explicit IEEE FP32 with neural
FP16 plus the existing first-hidden-branch flag, while the physical head,
native skip, tail/output and inverse remain FP32. Preserve original model
configuration, tensor bytes, parameter identities and Python/Torch/CUDA RNG.
Verify the actual model and distinct DINO hashes against the completed pilot.
No checkpoint export, default change, training or automatic full-frame run.

## Paired data and complete coverage

One original model is loaded at a time. Each complete noisy observation is
prepared once, then reused for both policies, alternating their forward order.
Targets and sensor-reference masks never enter the model's five-argument
boundary. Identity hooks verify those five actual tensors and one frozen-DINO
call per forward. Noise construction is source/case-keyed; reference tensors
and physical inputs must stay unchanged. Auxiliary scores run in canonical
IEEE FP32 on CPU after the physical FP32 predictions are saved/transferred.
No repeated RawNIND/classical inference is needed for this within-model policy
comparison; original baseline studies remain separate.

For each model retain:

- All427 fixed validation photos and16 procedural sources at native256/B2,
  seven original noise/exposure conditions and four CFAs:12,404 paired cases.
  Use the original validation membership/order, seed42 crops, protocol noise
  seed20261014, original WB/matrix and canonical8px metric border.
- All known4 and unseen5 development scenes,8/10 pairs and72/90 prepared
  crops, native512/B4 and original32px scoring border. Keep sensor-CFA scores
  primary and label the independent AHD renderings as auxiliary, not GT.
  Use the frozen prepared crops/conditioning; never decode source originals.
- The full14-signal analytic panel:12 carriers from levels`.01/.18`,
  contrasts`.02/.10`, periods`4/8/16`, plus two flat levels; ADC-only and
  highest-noise conditions at four CFAs/four draw labels. Preserve all448
  original labels per method. Compute ADC once per physical observation and
  retain its four aliases:280 actual observations in70 B4 fixtures, rather
  than recomputing identical zero-noise draws. Keep every individual case,
  every12 ADC carrier mean and all flat/noncarrier/quadrature values.
- All1,176 existing frozen color-grid inputs, both noise conditions and all
  CFAs. Save each full physical FP32 output for independent scalar replay.
  Keep the original three preview cases plus the four previously fixed peach,
  pink, amber and purple cases; choose these before new inference.
- Fresh paired outputs for all four standing GFX contexts and the two fixed
  sign/platform contexts. Source RAFs and siblings remain outside training.
  Use cached arrays, original coordinates/transforms and exposure4/+2EV.
  DSCF3880 ISO100/f5.6 is an independent qualitative reference, not GT; no
  reference-image pixel score is computed.

This gives14,028 actual observations per policy/model, retaining14,196 labeled
cases when deterministic ADC aliases are included. Save all physical maximum/
RMS differences before clipping or quantization, and complete per-case metrics
even if a numerical noninferiority limit fails. Do not replace failures by an
average or stop early on an unfavorable quality result.

## Prospective quality limits

Every natural-photo and procedural observation must lose at most`.05dB` in
sRGB and camera-linear PSNR and at most`.0001` in sRGB SSIM versus that same
model's fresh FP32 output, using the canonical border. Each prepared camera
crop must lose at most`.05dB` in sensor-CFA and auxiliary AHD sRGB PSNR and
at most`.0001` auxiliary sRGB SSIM. Missing/nonfinite required scores fail
execution rather than silently passing. Retain source/scene-balanced means,
source-bootstrap intervals, every condition and418/416-source sensitivities
in the eventual analysis; they cannot hide an individual failure.

Every analytic carrier, including all ADC layouts, must lose at most`.05`
signed gain. Each flat observation must retain spatial-luma RMS at most1.25×
FP32, including ADC fields; no floor is added to hide a nearly zero baseline.
Each hue field must increase maximum absolute channel-mean error by at most
one normalized camera DN16 and retain centered camera-RGB RMS at most1.25×
FP32. Keep mean bias, coherent gain, quadrature and false spatial energy
separate. These are strict expanded-scope requirements; a finite-pilot pass
does not predict their outcome. The earlier FP32-autotuning1/.25DN16 gate
remains unchanged for its original intervention, not redefined for FP16.

The original two-photo/ramp finite-pilot evidence stays bound. A fresh CUDA
execution preflight reuses both photos, all-CFA ramp/one-DN pair and B4 GFX
contexts, comparing each policy with its **matching-policy** saved pilot
output at1DN16 maximum/.25DN16 RMS. This checks execution parity, not mixed-
precision equivalence. Original ramp code/one-DN limits remain required.

## Execution, resources and native review

Before CUDA, require focused gate/artifact tests and genuine CPU execution of
both checkpoints: native64, two fixed eligible photo sources plus one
procedural source, ADC/highest noise and all CFAs. Compare an ordinary direct
FP32 forward with the paired runner exactly. The CPU half mode is explicit
engineering emulation, not a quality, timing or fake CUDA result. Count all
actual forwards and boundary/DINO calls, including the direct controls.

The separately detached controller first verifies all previous exact owners
exited. Run CPU proof, fresh CUDA execution parity, then V43 and V63 full
quality workers serially. Require48GiB available RAM stable for60s before GPU
work,24GiB active headroom, root64GiB/external500GiB reserves and a16GiB CUDA
allocator cap. Bound preflight workers to1,800s, each full worker to7,200s and
resource waiting to1h. Stop only exact owned children on a resource/runtime
failure. Preserve failures; no automatic retries or changes to the plan.
Estimated additional quality output is under6GiB on the local SSD; a later
full-frame study needs its own storage accounting.

Each policy/model emits two native160 exact-GT photo triplets and all standing
GFX regions, with source/ROI/checkpoint/noise/exposure metadata. The seven
complete merged boards cover88 triplets/132 native cells: photos, known,
unseen, analytic, hue, GFX and highlights. Never resize panel pixels.
Actually inspect all132 cells before interpreting quality summaries. CPU
coverage/scalar/source audits and the full per-case limits must pass before
calling the policy qualified. Keep every unfavorable field and source.

Only after that decision may a **separately frozen** actual100MP16-bit study
proceed, with warmed and startup timings, full unquantized differences,
linear/sRGB16 TIFF verification and exact native ROI checks. No native-context
ratio substitutes for a whole-photo result. This qualification left its
V43/README reference and production defaults unchanged;
[current model choices](current-model.md) reflect later quality work. Broad model quality, decisive
real-photo superiority and100MP/10s remain open.
