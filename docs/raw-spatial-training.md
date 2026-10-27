# V131/V132: full-budget spatial-detail trial

**The matched20k comparison is queued; all four new CPU/CUDA checks passed.**
V131 continues V120's architecture and V132 adds the optional
[RAW spatial branch](raw-spatial-features.md). Both use the cleaned90,781-photo
cohort with29 reviewed regions. Production waits for V125's memory admission.
Quality is unmeasured; V120 remains the general recommendation.

[Control recipe](../configs/quality-v120-raw-spatial-v131.yaml) ·
[Spatial recipe](../configs/quality-v120-raw-spatial-v132.yaml) ·
[Runner](../scripts/train_raw_spatial_trial.py) ·
[Setup, actual checks and owner bindings](results/raw-spatial-training-setup-v1.json).

## Matched recipe

Both arms start freshly from V120's completed20k EMA, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
Only `model.raw_spatial_features` differs. The official frozen DINOv3
ConvNeXt-Small revision, encoder hash and license remain unchanged.

| Setting | Both arms |
| --- | --- |
| Data |90,781 Commons sources/29 regions;32 paired scenes;128-scene native manifest,106 training scenes |
| Augmentation | Geometry before final area reduction; zero optical PSF; reviewed-region quota.5; photographic low-contrast fraction.25 |
| Observations | Seed70, native256/B16/BF16, one sensor view |
| Loss | Existing Charbonnier reconstruction; feature/shadow/band/conditional-mean additions off |
| Schedule |20,000 new updates, LR1e−5,100-step warmup, cosine horizon20,000 |
| Domain batches |10,046 Commons /4,965 native /4,989 paired |
| Per-arm budget |20,000 training/optimizer updates,640 validation forwards,20,640 encoder calls,320,000 target contexts |

Every source/domain, clean-batch and noisy-batch hash must match the control,
including the first18 exact-recipe CUDA check inputs. A hardlinked step1,000
progress checkpoint is retained within the same live worker and original20k
schedule, after validation. Atomic replacement of `last.pt` preserves it.
It is not a completed endpoint. The early comparison below is now queued.

## Early retained-input comparison

A separate live queue waits for each immutable1,000-step progress snapshot
while the original20k workers continue. Each model gets102 IEEE FP32 calls:
64 saved shadow observations,16 ordinary material inputs, four main-GFX512px
contexts, two mesh768px fixed profiles and16 faint-ADC observations. All V120
predictions are reused; V132 also compares the saved V131 progress predictions.
Every1,000-step clean/noisy training hash must agree between the two snapshots.
[Queue implementation](../scripts/queue_raw_spatial_progress.py) ·
[Verified inputs, real saved-state checks and live owner](results/raw-spatial-progress-review-setup-v1.json).

Step,20k horizon, parent,91/114 EMA tensors and89/112 Adam states at1,000 are
checked before model construction. The snapshot may belong to the exact live
training worker or the same completed worker's matching prefix. Collection does
not pause training, restart a schedule or repeat an old model. It uses52GiB
admission,12GiB CUDA cap and32GiB runtime floor, waiting up to48h for headroom
within its original absolute observation deadline. CPU reporting and independent
FFT/native-pixel audits follow automatically, including exact synthetic-GT
triplets and accurately labeled approximate real references. Actual viewing and
quality outcomes remain pending. Four material sources do not become independent
photographs through different noise/CFA conditions. The full endpoint chain below
keeps its original source and call budgets.

## Executed checks and admission

Each arm completes16 updates plus an actual two-update resume on CPU128/B1/FP32
and CUDA256/B16/BF16. All18 input hashes match per device. First RGB/auxiliary
outputs match65,536 values on CPU and4,194,304 on CUDA. Changed shadow-option
resumes reject before construction. V131 has91 restoration tensors/89 Adam
states; V132 has114/112, with finite nonzero gradients in all23 added tensors.
CUDA peak allocation is7,041,804,800/9,048,249,856 bytes respectively.

Total:72 discarded training/optimizer/encoder calls and612 target contexts.
Independent CPU inspection checks all eight16/18-step checkpoints and
1,053,314,052 finite saved values, optimizer steps, first outputs and input
hashes, with zero neural/noise/RAW/CUDA work.

The controller adopts those completed checks and waits until the exact original
V125 worker has obtained its64GiB startup admission, or the mean trial completes
successfully. New arms run sequentially with52GiB admission,16GiB CUDA cap,
32GB runtime floor and48-hour worker limits. Original workers, receipts, sources
and budgets remain intact; no check or training prefix is repeated.

## Quality and native review

The queued endpoints use the427-source photo panel, known/unseen cameras,
texture/color probes, all six main GFX regions and complete102MP RGB16 output.
Independent saved-array audits prepare local-detail/numerical contrasts against
V120/V117 and V131 versus V132. Reports include at least two native100%
noisy/restored/GT triplets with shared coordinates/transforms and recorded
checkpoint, noise and exposure. Scores and actual viewing are pending.

Both new models receive identical32-pixel full-frame tile grids. Whole CFA-cell
padding preserves native pixels; RGB returns to8746×11662. The original520
tiles/130 batched calls remain unchanged, and actual input fingerprints must
agree. Older saved pipelines keep their original tiling/profile; differences
are labeled in images/receipts and cannot isolate a model-only effect.

The extra fence queue uses **DSCF3842 ISO6400 / corrected DSCF3835 ISO100 f/5.6**,
both camera JPEGs, two fixed profiles and both native160 regions. The main
DSCF3879/3880 scene includes foliage and chain-link crops. Real ISO100/AHD and
JPEG references are qualitative, not exact GT: aperture, time and moving subjects
differ. Cached media are reused; originals remain read-only and scenes/siblings
remain outside training.
