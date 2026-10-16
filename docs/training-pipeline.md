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
Full preparation is queued after the batch sweep and full-frame review to avoid
competing with throughput measurements. Excluded sources remain excluded; only
training rows enter the training loader. Use `manifest` for the new 4× training
selection and explicitly retain the original 8× audited `validation_manifest`
in a new experiment configuration. Validation source hashes and source snapshots
are recorded, and resume rejects a changed validation/augmentation recipe.
Newly downloaded images are not silently admitted by this frozen rebinning job.

This option currently applies to Commons/procedural clean RGB. Registered
paired RAW retains exact sensor-phase transforms. Native-RAW synthetic targets
still use their existing 8× camera-linear caches and augmentation; extending the
same sampling order there requires a separately prepared 4× native cache.

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

The sweep is running on the existing 8× data path so only batch size varies.
Larger batches change samples per optimizer update and are not a convergence
comparison. A new batch size must be evaluated for image quality; throughput
alone does not justify scaling LR or claiming a better model. The 4×→2× path
also needs its own throughput check before choosing its production settings.

Validation: **248 tests passed in 20.53s**, including sampling precision,
projective/constant-color behavior, frozen source splits, live WAL ingestion,
selected-domain fetch guards, and deterministic mixed-data restart. Ruff passed.
