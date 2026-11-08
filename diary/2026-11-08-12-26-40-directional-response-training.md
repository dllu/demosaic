# Directional response GPU admission and matched training

Recorded: 2026-11-08T12:26:40-08:00 (America/Los_Angeles).

After the storage cleanup, resumed the fine-dark-detail objective. V195 GPU
admission passed from the completed V187 EMA donor, retaining its trained
508-parameter head and all 189 frozen V183 tensors. All 103 neural sources remain
unchanged. Seven native initial parities and six trained-head CPU/GPU checks
passed. Each loss variant performed two genuine training-only probe updates and
restored model/Adam/EMA/CPU-CUDA RNG state after its first update. The four probes
checked 2,032 parameter-gradient coordinates; both directional output derivatives
matched the independent NumPy spatial calculation exactly after FP32 conversion.
The largest head-gradient CPU/GPU difference was 1.64509e-5, within the prospective
5e-5 relative/2e-5 absolute tolerances. CPU inspection completed eight strict
raw/EMA loads and 1,512 inherited tensor comparisons without forwards.

The two matched training jobs were launched once: whole PID1574829/create
1794169364.29 and directional PID1575152/create1794169471.59. Both use the same
V187 EMA full module hash4739e107a2460166dae5f14c7d89415b4b0c1ccc689d5a3480787ffa1696ebc4,
fresh Adam/EMA clocks0, seed202611080195, 1,000 cached rows, 900 noisy updates,
3,600 images and100 ADC skips. Existing penalties, masks, weights, FP32 order,
schedule and clipping remain fixed. Whole adds .25 domain-weight coherent
response; directional adds .25 domain-weight eight-region response. Equal nominal
weights do not imply equal gradient norms. This is fresh matched retraining from
a trained head, not continued old Adam history. Probes are excluded as initializers.

Five factored checkpoints and a true row8 restoration are planned for each arm.
The complete independent trace validator passed an explicitly structural fixture
based on prior rows with a zero tenth term, and rejected an altered tenth term.
The actual independent training/quality audits remain pending. No protected
capture enters optimization; GFX inputs were used only for initial inference
parity. No source/noise draw, RAW decode, parent/DINO call or original/dataz access.

Selective source closures occupy under2 MiB per stage. The prospective total new
local output budget is2 GiB, including all four endpoints' native evidence,
compact current-comparator panels, exports and reports. Reuse datasets,
manifests, parent arrays and earlier native encodings rather than recopying old
artifacts. No external writes. Reserves: local40/RAM32 GiB, launch RAM52 GiB,
CUDA quota24 GiB. All822 held-out cases per endpoint, both GFX families and actual
100% crop inspection remain required; no learned quality or flat-safety claim.

[GPU admission and matched-training preparation](../docs/results/v195-directional-response-GPU-preparation-v1.json)
and [current loss/training guide](../docs/directional-pair-response.md). Original
scientific roots are `.cache/quality-20261108/V195-directional-response-admission-v1`
and `.cache/quality-20261108/V195-directional-response-trial-v1`.
