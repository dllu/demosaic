# Documentation guide

Start with the [README](../README.md) for setup,inference and representative
native crops. **V102 final20k is the current quality baseline**, continuing
V84's DRUNet RGB/frozen DINOv3 ConvNeXt-Tiny architecture. It gains+.176dB over
V101 on full427 and raises both measured-camera means. V103 is a close
alternative; V102 has lower ADC flat-color error and stronger tested weak texture.
[Completed study and native comparisons](v102-v103-quality-review.md).
All seven evaluation panels and complete102MP GFX exports have finished.
V104 is training from V102 on the newly reviewed90,872-source cohort; its
production quality remains unmeasured.

| Topic | Start here |
| --- | --- |
| Current work | [V84-family cleaned-data/fine-detail training](quality-first-training.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V102/V103 quality and comparisons](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) · [Linear DNG/JPEG export](dng-export.md) |
| Data | [Next90,872-source corpus and native review](incoming-commons-quality.md), [prior Commons corpus](commons-post4557-reviewed.md), [source quality](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
| Training | [Data/augmentation pipeline](training-pipeline.md), [execution/restart](training-execution.md), [V43 quality-study checks](quality-training-validation.md) |
| Evaluation | [Quality/noise diagnostics](evaluation.md), [natural fine detail](heldout-detail.md), [noise/detail tradeoff](noise-conditioning.md), [ADC-only consistency](adc-consistency.md), [GFX test](gfx-qualitative.md), [prepared test reserve](paired-reserved-test.md) |
| Method research | [Research/design record](research.md) |
| Remaining requirements | [Current completion checklist](requirements.md), [historical progress log](requirements-archive.md) |

Per-experiment reports contain numerical evidence, source/ROI metadata,
checkpoint hashes, noise/display settings and native triplets. Study-specific
eligibility gates do not prevent showing useful versions or changing the current
baseline. Timestamped historical decisions belong in the diary. Real low-ISO or
independently demosaiced references are labeled accurately. Machine receipts
retain recorded UTC timestamps; diary filenames use America/Los_Angeles time.
