# Historical 4k photo sensitivity to known related source series

Removing the identified capture-series/site sources barely changes the original
V64-minus-V63 rendered-photo effect. It remains small and uncertain. **Keep the
original 4k no-promotion decision.** This is a reanalysis of already saved scores,
not a new model, inference run or scene-independent benchmark. The actual 20k
expanded run and its full review remain pending.

[Executed 63 comparisons, independent arithmetic and retained native crop metadata](results/commons-source-sensitivity-first4k-v1.json).
[Original full 4k review](long-commons-v63-v64-first4k-review.md).
[Content review and fixed source policy](commons-content-overlap.md).

Both 4k arms retain their original 20k schedules, common V60 initializer, seed 49,
B16/native 256×256/BF16 training recipe and unchanged native/paired domains. Their
Commons membership is 40,170 versus 66,934. These models did not train on the new
84,867-file future quarantine. Quarantining future training files does not erase inherited
restoration/foundation-model exposure; pretraining overlap remains unverified.

## Data effect on the fixed photo subsets

The content/metadata policy was frozen before either 20k full 427-photo panel runs.
For this older 4k result it is a post-hoc source sensitivity, not a new blind test.
Original 427 scores are preserved; known capture-series exclusions retain 418,
and adding known shared-site exclusions retains 416. Narrow metadata groups do
not establish independence for the remaining sources.

| Photo source set | V63 sRGB PSNR | V64 sRGB PSNR | V64−V63, dB[95% source interval] |
| --- | ---: | ---: | --- |
|Original 427|35.76802|35.78297|+0.01495[-0.00080,+0.03320]|
|Known series excluded 418|35.76100|35.77447|+0.01347[-0.00045,+0.03143]|
|Known series/sites excluded 416|35.77105|35.78456|+0.01351[-0.00123,+0.03189]|

Linear PSNR retains a positive source interval; sRGB PSNR and SSIM intervals
still include zero on all three sets. The mean rendered-PSNR difference moves
by only about −.0014 dB after exclusion. This does not estimate the bias of every
unknown related scene, demonstrate convergence, or determine whether larger
data helps at the original 20k endpoint. Historical V60/V58/V43 comparisons are
also retained in the receipt, with their different training histories.

Each source averages all seven conditions/four CFAs before paired comparison.
Bootstrap uses 1,000 source draws/seed 42, separately for each declared set, with
linear .025/.975 quantiles. These intervals concern image-source variation within
that fixed set. They do not include training-seed, source-curation/selection,
unknown scene-family or foundation-pretraining uncertainty.

## Actual execution and independent verification

The [score operator](../scripts/report_commons_source_sensitivity.py) verifies
input statistics/cohort hashes, checkpoint/model-label bindings, complete unique
photo/noise/CFA coverage and shared observation metadata. Unchanged classical
witnesses retain their previous four-float32-ULP post-hoc bound; no exact replay
or relaxed bound is claimed. All 21 published full-panel comparisons reproduce
exactly before adding 42 source-subset comparisons:63 total, five actual models.
Retained/excluded source contributions reconstruct each original mean.

The [independent auditor](../scripts/audit_commons_source_sensitivity.py) imports
no production aggregator. Decimal 60-digit accumulation rebuilds 179,340 raw
case-metric values and 6,405 source means; all means match exactly. Independent
scalar bootstrap sums/manual linear quantiles check 420 statistic scalars over
all 63 comparisons, maximum difference 2.22e-16. The specified PCG64 draws are
separately reconstructed and byte-bound. No metric definition or restored pixels
are recomputed. Six focused tests also pass, including complete-cell rejection
and the known interval of exhaustive two-source resampling.

All work is CPU-only, with no model load, RAW decode, new target/noise draw,
optimization or protected-final score. Executed operators/source means/receipts
remain under
`/mnt/external/demosaic/benchmarks/commons-source-sensitivity-first4k-v1/`.

Reproduce into a new directory:

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' uv run --no-sync python scripts/report_commons_source_sensitivity.py \
  --statistics docs/results/long-commons-v63-v64-first4k-review.json \
  --statistics-sha256 0aa271bab1d4e57256394a007c3a61a57c812f55c917d0d8bc97f454b2f4b8ca \
  --cohorts /mnt/external/demosaic/commons-known-series-quarantine-20261017-v6/prospective-development-cohorts.json \
  --cohort-sha256 45c7e74e1db348aca3d4cd3ed5580394cd4914b641ebb281b21fa86ff7b26a80 \
  --output /mnt/external/demosaic/benchmarks/commons-source-sensitivity-first4k-reproduction
CUDA_VISIBLE_DEVICES='' uv run --no-sync python scripts/audit_commons_source_sensitivity.py \
  /mnt/external/demosaic/benchmarks/commons-source-sensitivity-first4k-reproduction
```

## Unchanged native photographic triplets

These four original PNGs were reopened at original resolution; their hashes and
paired noisy/GT pixels verify. Each model has two 160×160 native noisy WB-aware
Malvar→denoised→exact saved simulated-GT panels, with no resizing. Both sources
remain in all three subsets. ROI `[48,48,160,160]` in native 256×256, RGGB,
WB `[2,1,1.5]`, fixed protocol matrix, shot=.00256/read variance=.0000262144,
16-bit ADC/black=.03 and display ×1/0 EV match. Predictions are the retained original
CUDA FP16 evaluation; PNGs are 8-bit sRGB previews at the 8×-binned resolution.

Step 4,000 checkpoint SHA256:

- V63: `5f29bd7efb94b72491cff22575c0565995326644823bcb802444214c8f2c6bd6`.
- V64: `c0a00177b676caddea39b225f2fba1bcdc0b57d6fd543500363c8c908d83df81`.

Sources: [Roy Egloff](https://commons.wikimedia.org/wiki/File:CH.VD.Villeneuve_2007-08-25_Vertigo-Swiss-Riviera_2392_3x2-R_4K.jpg)
and [Dietmar Rabich](https://commons.wikimedia.org/wiki/File:Vancouver_(BC,_Canada),_Coal_Harbour_Seaside_Park,_Blick_in_den_Himmel_--_2022_--_2158.jpg),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), modified by binning,
cropping, simulated noise and restoration. Full source IDs/protocol/reference/
checkpoint/ROI metadata accompany each crop in the receipt.

V63 control, fabric and building:

![V63 fabric: noisy, denoised, exact simulated GT](images/long-data-first4k-full427-crop-b414022291d49a12.png)

![V63 building: noisy, denoised, exact simulated GT](images/long-data-first4k-full427-crop-4caf1ed5a1a68663.png)

V64 expanded, the identical observations:

![V64 fabric: noisy, denoised, exact simulated GT](images/long-data-first4k-full427-crop-3637d85e75a7da62.png)

![V64 building: noisy, denoised, exact simulated GT](images/long-data-first4k-full427-crop-0129a7049da1d309.png)

Fabric cords remain absent and facade/cloud details soft, with no convincing
native expanded-data advantage in these fixed examples. Existing paired-real,
analytic/hue and standing GFX results are unchanged; see the original review.
GFX ISO100 AHD remains an independent reference, never exact GT. This source
sensitivity neither replaces those panels nor promotes a model.

## Pending original 20k application

The future statistics file is
`/mnt/external/demosaic/benchmarks/long-commons-v63-v64-full20k-final-review-workflow-v1/primary-saved-comparisons.json`.
It is absent at capture. After the actual original workflow closes, apply the
same source-sensitivity operator/auditor to that completed file and its actual
hash. That path has not executed yet; no 20k scores are inferred from this 4k
check. Original 427, additional418/416 comparisons, all 56 new native views and
the full quality decision remain required. SOTA, decisive real-photo superiority
and 100MP within 10 seconds remain unmet/unproven.
