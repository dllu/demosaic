# V104 ADC texture tradeoffs and full-photo review queue

Recorded: 2026-10-23T17:01:27-07:00 (America/Los_Angeles).

Completed a prospective V104 final20000 CPU FP32 comparison of three output
policies on 48 deterministic ADC-only carrier/CFA cases and eight flat fields.
One copy of each ADC case avoids counting the former four identical draws as
independent evidence. Levels .01/.18, contrasts .02/.10, periods4/8/16, all four
CFAs; original/Malvar/sites share each actual neural prediction. No training,
checkpoint, active selector or positive-noise loss-scale plan changes.

At bright level.18/contrast.02, Malvar changes mean in-phase gain:
period4 .92019→.93348, period8 .98626→.99928, period16 .98215→.99995.
However, linear-sRGB RMSE improves in39/48 carrier cases and regresses in9;
noncarrier RMS rises in18/48. Sites improves carrier RMSE in48/48. Both improve
flat-field RGB RMSE in7/8, with one small regression each. Thus the earlier
flat-color tail repair does not by itself choose the ADC output policy.

Included four native examples fixed before inference, plus the posthoc largest
Malvar carrier RMSE increase. That adverse case is bright level.18/contrast.02,
period4, GBRG: gain .87907→.78821, RGB RMSE .00095437→.00103016; sites gives
.00092788. Its original RGB8 appearance is close, but the numeric loss is real
and hidden by the four-CFA mean. Reused saved floats for the adverse crops;
no extra neural forward or target fitting. All methods share the same
native160 ROI and display; analytic references are exact GT.

Verified all91 final EMA tensors, the official frozen Tiny state,59 real
DINO-backed forwards, unchanged weights/configuration/parameter IDs/inputs
and per-forward Torch RNG. Those59 forwards comprise56 ADC inputs and3
whole-model forwards on a mixed batch of four positive-prior inputs, spanning
all CFAs and shot-only/read-only/combined priors. Enabling either ADC operator
in production reproduces all four original positive-noise outputs byte-for-byte.
The original runtime flags and zero-noise conditioning were restored.

Independently rehashed all56 input archives and224 prediction arrays, rebuilt
all1504 scalar metrics and grouped statistics in NumPy64, and rerendered45
native panels exactly. Viewed all25 board cells at original resolution:
20 fixed and5 posthoc adverse. Published15 triplets with source,ROI,weights,
conditioning and display metadata. The docs now combine completed color and
texture evidence, with the remaining photographic test explicitly pending.
[Current report](../docs/v104-adc-color-projection.md) ·
[Completed execution/audit/actual-viewing receipt](../docs/results/v104-adc-texture-projection-v1.json).

Added a separate CPU-only postprocessing queue bound to the exact existing
full427 photo controller/child PID+creation and frozen plan. It waits for their
verified completion before aggregating5124 rows/10k source-bootstrap intervals,
then reruns the exact original partner batches to show each policy's weakest
source-mean PSNR change and largest chroma increase. Both operators are shown
on every selected case, with the ROI chosen from the respective error map.
Ten fixed and20 adverse native cells will await actual visual review; the
queue cannot publish a recommendation or restart the study.
[Verified queued handoff](../docs/results/v104-adc-photo-review-queued-v1.json).

At17:01 PDT the photographic run had completed98/427 sources/1176 score rows;
V111 was healthy at logged step4675, with V112 and the declared quality,
full-frame and material queues still waiting. All eight existing/new active
PID+creation handles were live. Available memory was73.9GiB and external SSD
free space267.8GiB. Originals remained untouched and no source HDD was read.

Final verification: 27 receipt reference occurrences/21 unique hashes,
all15 public triplets and25 native cells checked, 165 local Markdown
links/fragments across9 files,9 unchanged frozen plans and8 live exact
PID+creation handles. Maximum independent NumPy64/Torch64 metric discrepancy:
1.75e-14. Current selector and historical machine receipts retain
original bytes. Validation is actual numerical/display/ownership evidence;
no additional restoration implementation or training configuration was changed.
