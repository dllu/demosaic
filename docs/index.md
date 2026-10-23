# Documentation guide

Start with the [README](../README.md) for setup, inference and representative
native crops. **V101 is the fully benchmarked default**, continuing V84’s DRUNet RGB
trunk and frozen DINOv3 ConvNeXt-Tiny features. The completed cleaned-data/detail
comparison shows a small widespread photographic gain with close camera means.
V102/V103 now compare six versus32 reviewed regions on the separate88,477-source
cohort. V102's original20k endpoint now leads the selected-detail comparison,
with +.29dB ISO100 over V101 and improved scores in all12 cases. The README,
[detail gallery](heldout-detail.md) and GFX guide show its current crops. V103
is running; full matched evaluation remains queued. Completed full-frame
comparisons remain alongside the newer cached-context results.

| Topic | Start here |
| --- | --- |
| Current work | [V84-family cleaned-data/fine-detail training](quality-first-training.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V101/V102 quality and comparisons](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) |
| Data | [Commons corpus](commons-post4557-reviewed.md), [illustrated source review](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
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
