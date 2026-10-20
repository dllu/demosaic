# Native and numerical review of the mature precision pilot

The saved-output review tools pass a genuine historical CPU preflight. All24
original FP32 photo/GFX triplet PNGs replay byte for byte; both boards retain
all36 native160px cells. All29 physical-input fingerprints match the producer.
The NumPy analytic implementation replays576 historical rows exactly and
agrees with640 independently computed Torch fields within1.29e-14. No new
model inference or CUDA initialization is involved. This is engineering
evidence, without a new FP16 quality or speed result.

The original [pilot](mature-mixed-precision-pilot.md) and its live GPU source
bundle remain unchanged. A separate source-frozen postprocessing plan is kept
under `.cache/benchmarks/mature-mixed-precision-REVIEW-v2/`. It binds the exact
GPU plan, canonical metric code, independent math, renderer, shared crop
registries and historical preflight. The GPU job remains serial behind V92's
training/review/closure/reference/native-package jobs.

The first frozen-copy preflight correctly rejected an output directory outside
its frozen workspace. That failed v1 plan is retained. The corrected v2 plan
places display outputs under `work/outputs/`, satisfying the existing output
guard without changing production safety code or the live GPU plan.

## Fixed scopes declared before the pilot produces output

- Each of six model/policy methods contributes two exact-GT photo triplets and
  four GFX triplets:36 triplets /48 unique native cells across two boards.
  Photo ROIs are `[48,48,160,160]` within native256 predictions. GFX ROIs are
  `[176,176,160,160]` within their original native512 contexts, at exposure4.
  The standing DSCF3879/3880 pair includes sky, building, foliage and fence.
  The separate ISO100 capture is labeled **not GT** and receives no pixel score.
- Photo PSNR/SSIM uses each complete native256 output, common sRGB transforms
  and exposure1. Retain canonical production FP32 metrics and separate NumPy
  float64 reductions. Historical arithmetic differences reach2.32e-6dB and
  6.01e-6 SSIM; the implementations are not bitwise equivalent. Require the
  fixed .05dB/.0001 noninferiority gates to pass under both implementations.
  Record disagreement explicitly; do not loosen thresholds or choose the
  favorable implementation after seeing output.
- Analytic metrics use linear sRGB, native160 ROI at48,48, retaining all96
  unique observations per method:48 ADC carriers,32 noisy carriers and16 flat
  observations. Retain all12 ADC group means and each individual CFA/draw.
  Four historical deterministic ADC draw labels name one actual observation;
  record all192 labels without treating duplicates as independent data.
- Apply signed-gain loss at most.05 to each ADC and each noisy weak-carrier
  observation, and flat-luma spatial RMS at most1.25×FP32 to each flat
  observation. These conservative per-observation checks prevent favorable
  group means from hiding a failed CFA/draw. Preserve DC, quadrature,
  noncarrier, band-energy and RMSE values separately.
- Audit all174 capture arrays, all24 timed repeat arrays, observed physical/
  encoder dtypes,110 source observations, checkpoint/DINO identities and
  successful exited GPU owners. Record unquantized camera-RGB max/RMS DN16
  differences over every full saved fixture, including ramps and GFX. The
  earlier FP32 autotuning1/.25DN16 gate is not redefined for FP16.
- Reopen the actual all-CFA ramp pair, verify the packed input differs by one
  FP32-representable16-bit code and all other fields agree, then require more
  than256 output codes and a nonzero one-DN response per model/policy/CFA.
  A half-policy screen also requires its FP32 ramp control to pass.
- Preserve every first-policy-call duration separately and all four balanced
  resident timing samples per policy/model, including repeat-output checks.
  Median speedup is `FP32_median / policy_median - 1`. The original5% on both
  models requirement remains descriptive eligibility for a separately frozen
  follow-up, never an automatic full-frame run or production change.

## Run after actual successful GPU completion

Use the frozen copies and CPU-only environment:

```bash
source scripts/env.sh
precision_review_root="$PWD/.cache/benchmarks/mature-mixed-precision-REVIEW-v2"
precision_review_work="$precision_review_root/work"
export CUDA_VISIBLE_DEVICES=''
export PYTHONPATH="$precision_review_work/src:$precision_review_work/scripts"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
.venv/bin/python3 -P "$precision_review_work/scripts/render_mature_precision.py" \
  .cache/benchmarks/mature-mixed-precision-CUDA-v1/plan.json \
  /mnt/external/demosaic/benchmarks/mature-cudnn-autotune-v2/native/report.json \
  "$precision_review_work/outputs/native" \
  --GPU-receipt .cache/benchmarks/mature-mixed-precision-CUDA-v1/work/GPU-output/receipt.json
```

Actually open both resulting boards at original pixel scale and inspect all48
cells **before** computing new quality/timing summaries. Write the manual
viewing receipt only after viewing: status
`actually-viewed-all-native-mature-precision-cells-before-scalars`,
`render_index` reference, actual `observed_UTC`, `new_scalars_interpreted: false`,
and two `boards` records with exact `receipt`/`image` references,
`native_cells_viewed` and observations. Include four `per_policy_findings`
records, one per model/half policy, with `model`, `policy`, boolean
`no_visible_new_artifact` and concrete `notes`. A generated or historical
viewing receipt cannot complete this step.

```bash
.venv/bin/python3 -P "$precision_review_work/scripts/review_mature_precision.py" \
  "$precision_review_root/plan.json" \
  .cache/benchmarks/mature-mixed-precision-CUDA-v1/work/GPU-output/receipt.json \
  "$precision_review_work/outputs/native/index.json" \
  "$precision_review_work/outputs/manual-native-viewing.json" \
  "$precision_review_work/outputs/scalar-review"
```

The reviewer rejects absent/incomplete viewing, live or failed GPU owners,
changed source/input hashes, missing policy/case coverage and altered dtype/
state evidence. It retains588 photo/analytic rows,90 analytic group means,
24 ramp checks and116 full-fixture physical comparisons. No current FP16
result or completed pilot is inferred from the historical preflight.
