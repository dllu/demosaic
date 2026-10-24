# Documentation guide

Start with the [README](../README.md) for setup, inference and representative
native crops. **V104 final20k is the working baseline for positive-noise RAW
and continued quality training.** It reaches 36.80085dB on full427, +.12134dB
over V102, improving 424 source means and the tested weak texture. V102 retains
lower ADC flat-color bias and a higher unseen-camera mean.
[Completed V104 results and native comparisons](v104-reviewed-corpus-quality.md).
All seven V104 panels and complete102MP exports are finished. V111 completed20k
on90,864 sources and [improves all twelve material cases](v111-early-quality.md),
with modest native gains and small real GFX changes. Its [complete camera
panels](v111-early-quality.md#complete-development-camera-panels) show a small known-scene
loss and unseen-scene gain. V112 has completed20k with a
smaller reconstruction loss scale; full matched evaluation is running.
[Actual trial and evidence](loss-scale-training.md).
The [completed material comparison](v111-v112-material.md) shows V112's gains
over V104 and close, mixed changes versus V111; high-noise fine detail remains soft.
The [V113 Small training queue](small-aligned-training.md) uses fitted feature
transfer with learned gates preserved and reuses completed V111 as its Tiny
control. Eight actual CPU updates pass; CUDA and fresh20k training are queued.
The [stronger RawNIND full-frame comparison](rawnind-fullframe.md) adds complete
GFX output and six native regions; fence and foliage weaknesses remain visible.
The optional [V104 ADC sites export](adc-consistency.md) adds .2885 dB on the
complete ADC-only photo panel, with unchanged learned weights and documented
flat-color tradeoffs.
The optional [eight-view inference mode](dihedral-quality.md) improves the fixed
V104 material/adverse-camera pilot with unchanged weights, at eight evaluations
per tile. Its full photo/camera/texture/color comparison is queued after the
existing GPU workflow. V111's [complete texture/color review](v111-early-quality.md#complete-weak-texture-and-flat-color-panels)
shows stronger coarse carriers and high-noise color, with a worse ADC bias tail.
The [current fusion-gate diagnostic](fusion-gate-quality.md) retains useful
DINO fusion: disabling it reduces selected color failures but weakens photo and
adverse-camera results, with little visible GFX change.
A [training-only Small feature fit](small-feature-transfer.md) retains these
gates and nearly preserves selected Tiny photo means; trained capacity and
complete comparisons remain pending.

| Topic | Start here |
| --- | --- |
| Current work | [V84-family cleaned-data/fine-detail training](quality-first-training.md) · [V104 loss-scale test](loss-scale-training.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V104/V102 choices and comparisons](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) · [Linear DNG/JPEG export](dng-export.md) |
| Data | [Reviewed90,864-source future corpus and native review](incoming-commons-quality.md), [prior Commons corpus](commons-post4557-reviewed.md), [source quality](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
| Training | [Data/augmentation pipeline](training-pipeline.md), [execution/restart](training-execution.md), [V43 quality-study checks](quality-training-validation.md) |
| Evaluation | [Quality/noise diagnostics](evaluation.md), [natural fine detail](heldout-detail.md), [RawNIND variants](rawnind-variants.md), [noise/detail tradeoff](noise-conditioning.md), [ADC-only consistency](adc-consistency.md), [V104 color/texture projection diagnostics](v104-adc-color-projection.md), [GFX test](gfx-qualitative.md), [prepared test reserve](paired-reserved-test.md) |
| Method research | [Research/design record](research.md) |
| Remaining requirements | [Current completion checklist](requirements.md), [historical progress log](requirements-archive.md) |

Per-experiment reports contain numerical evidence, source/ROI metadata,
checkpoint hashes, noise/display settings and native triplets. Study-specific
eligibility gates do not prevent showing useful versions or changing the current
baseline. Timestamped historical decisions belong in the diary. Real low-ISO or
independently demosaiced references are labeled accurately. Machine receipts
retain recorded UTC timestamps; diary filenames use America/Los_Angeles time.
