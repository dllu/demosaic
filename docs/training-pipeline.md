# Training data work, sampling order and batch size

The mixed trainer previously prepared a Commons batch on **every** optimizer
step, including steps that replaced it with paired RAW or native-RAW synthetic
data. Domain selection now precedes loading. Each loader samples only its
selected global steps, starts workers on first use, and stops prefetch at the
requested training endpoint. This removes discarded Commons augmentation while
preserving original sample indices, domain decisions and physical noise draws.

For seed45's first 1,000 steps, 514 select Commons/procedural, 230 paired RAW and
256 native-RAW synthetic. Batch4 formerly consumed 4,000 Commons examples
(plus possible unused prefetched work);
the new route prepares 2,056. **All 41 logged V30 observation/target fingerprints
were reproduced exactly** with selected-only loading. Unlogged observations were
not separately hashed. Mixed-domain interruption/restart tests retain identical
weights and EMA, and guards reject any fetch from an unselected domain.

## Augmentation before the final reduction

The optional `augmentation_downsample: 2` training path is:

1. Decode original Commons images with their ICC profile, convert to linear
   sRGB, and average 4×4 source cells into a uint16 cache.
2. Crop at twice the target resolution. Apply exact quarter-turns/flips.
3. When projective augmentation is drawn, combine crop-to-output scaling and
   projective rotation/shear in one resampling operation at twice the target
   resolution. Otherwise use area scaling at that resolution.
4. Apply sampled optical PSFs in final-pixel units at the higher resolution.
5. Average 2×2 linear cells to the final patch; then apply camera/exposure,
   Bayer masking, Poisson/read noise and ADC simulation.

There is no geometric interpolation after the last reduction. Synthetic detail
and smooth fields also use the higher intermediate resolution in this mode.
Interpolation error is reduced in a controlled test; it is not eliminated.
For one continuous cosine/projective fixture, MSE against a denser integration
reference falls from .00493965 to .00047290. This single sampling experiment is
not evidence of trained-model quality or universal improvement.

The loader requires metadata declaring 4×-binned caches, and outputs native
256px patches as FP32. Four actual source checks found at most one uint16 code
of difference between unaugmented 4×→2× reduction and the old direct 8× cache.
Source files and frozen manifests remain unchanged. Existing configurations
default to the original path, preserving ongoing experiments.

Prepare the same source selection at 4× without changing held-out membership:

```bash
source scripts/env.sh
uv run --no-sync demosaic prepare --source /mnt/external/qi \
  --output /mnt/external/demosaic/commons-frozen44732-bin4-v1 \
  --factor 4 --min-size 512 --workers 2 \
  --selection-manifest /mnt/external/demosaic/audits/commons-44732-v1/manifest.jsonl
```

The first 256 sources are prepared and checked (237 train/13 val/6 test).
Full preparation is running after the completed batch sweep and full-frame review,
which avoided competing with throughput measurements. Excluded sources remain excluded; only
training rows enter the training loader. Use `manifest` for the new 4× training
selection and explicitly retain the original 8× audited `validation_manifest`
in a new experiment configuration. Validation source hashes and source snapshots
are recorded, and resume rejects a changed validation/augmentation recipe.
Newly downloaded images are not silently admitted by this frozen rebinning job.

The option also applies to [native camera-linear targets](native-raw-targets.md#augmentation-before-the-final-reduction)
via `raw_clean_augmentation_downsample: 2`. Their4× cache is complete with the
same53 training captures/31 scenes. Registered paired RAW uses exact sensor-phase
transforms. Existing experiments retain their original8× configurations.

`scripts/freeze_rebinned_manifest.py` will freeze the complete Commons4× producer
output only after its lock is released and all active source identities/splits
match the audited selection exactly. Partial output, changed protected splits,
missing sources and an existing frozen manifest are rejected. A waiting owned
job will create `/mnt/external/demosaic/audits/commons-bin4-frozen44732-v1/manifest.jsonl`
after full preparation. [V34's matched augmentation recipe](../configs/dino-anchored-pre-downsample-b16-v34.yaml)
points there, with original8× validation; it cannot accidentally train on the
producer's current256-source manifest. V34 has not started.

For general ingestion while the archive downloads, SQLite now reads committed
WAL data in read-only mode and releases its metadata snapshot before decoding.
The old immutable connection could miss newly committed downloads. Frozen
selection rebinning reads its supplied manifest instead of the changing index.

## Batch-size sweep

`scripts/benchmark_training.py` runs fresh processes for batches 4/8/16/32/64,
two repeats in a deterministic shuffled order, using the same initializer,
model, frozen manifests, mixed-domain schedule, LR and data-worker counts.
It excludes 15 warmup steps and measures 45 steps per case. Timing includes
actual selected-domain I/O/augmentation, physical degradation/GAT conditioning,
frozen DINO features, forward/backward, AdamW and EMA. It excludes validation,
startup and checkpoint serialization. All cases must share the same source hash.

```bash
source scripts/env.sh
uv run --no-sync python scripts/benchmark_training.py \
  configs/dino-anchored-stabilized-rgb-v30.yaml \
  --initialize /mnt/external/demosaic/runs/dino-anchored-stabilized-rgb-v30/initialization-v30.pt \
  --output /mnt/external/demosaic/benchmarks/mixed-training-batch-sweep-v1
```

The completed sweep used the existing 8× data path so only batch size varies.
Larger batches change samples per optimizer update and are not a convergence
comparison. A new batch size must be evaluated for image quality; throughput
alone does not justify scaling LR or claiming a better model. The 4×→2× path
also needs its own throughput check before choosing its production settings.

| Batch | Mean images/s | Two-run range | Peak CUDA GB |
| ---: | ---: | ---: | ---: |
| 4 | 22.52 | 22.40–22.64 | 2.23 |
| 8 | 24.56 | 24.38–24.74 | 3.72 |
| **16** | **26.14** | **25.19–27.09** | **6.94** |
| 32 | 26.42 | 25.67–27.18 | 13.39 |
| 64 | 26.27 | 25.53–27.01 | 26.28 |

Choose **batch16** for the next quality trial: approximately16% more images/s
than batch4, within1.1% of batch32's mean, with about half its CUDA allocation.
The largest batch provides no measured benefit here. Ranges reflect two shared
machine runs, not confidence intervals; no claim of a unique hardware optimum.
Keep LR unchanged and review image quality before extending training. Peak CUDA
allocation is not total system RAM usage. All10 cases share the same archived
source hash. [Complete measurements and reproduction receipt](results/training-batch-sweep-v1.json).

[V31's recipe](../configs/dino-anchored-stabilized-rgb-b16-v31.yaml) continues
frozen V30 step1000 with batch16, retaining model/AdamW/EMA/RNG state and the
existing8× dataset. It stops after1,000 additional updates (step2000) for paired,
synthetic and GFX review. This processes16,000 additional examples and changes
global sample indices to the batch16 recipe. It is not an equal-image or
batch-only quality ablation. The complete4× selection prepares separately;
current training does not silently switch to its partial output.

A genuine DINO BF16 backward smoke on the actual 4×→2× Commons batch also passed:
finite FP32 output and nonzero measurement-adapter gradients. This verifies
execution, not the quality of a model trained with the new augmentation path.

Validation: **248 tests passed in 20.53s**, including sampling precision,
projective/constant-color behavior, frozen source splits, live WAL ingestion,
selected-domain fetch guards, and deterministic mixed-data restart. Ruff passed.

Subsequent [invariant-grid caching](expectation-grid-performance.md) removes
repeated Poisson table work without changing numeric outputs. The
[V31 quality review](anchored-rgb-b16-v31-review.md) finds synthetic gains but
real-camera regression after batch16 continuation, so V30 remains the quality
reference. Lower-LR/data-mixture trials are separate from the throughput choice.

The subsequent invariant-grid comparison reaches29.07images/s versus26.18
with the original table construction at batch16 (two alternating runs each,
same6.94GB allocation). Full validation including the native4 extension and
complete-manifest freeze gate now passes **256 tests**. Model quality remains
under development; these software/throughput checks do not establish it.
