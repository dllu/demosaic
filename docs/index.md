# Documentation guide

Start with the [README](../README.md) for setup, inference and representative
native crops. **V114 Tiny is the current general quality baseline**, with
36.97973dB on full427 and54.28627/54.00290dB known/unseen measured-CFA means.
V115 fitted Small has a higher known-camera mean and eight-pixel weak response;
Tiny has slightly higher photo PSNR and lower tested color bias.
[Completed comparison and native images](v114-v115-quality.md) ·
[Current choices](current-model.md). The optional [V114 eight-view fixed24 comparison](v114-eight-view.md)
adds material/camera gains and native examples, with selected color-bias tradeoffs
and unmeasured complete-panel/frame scope.

All primary/analytic panels, independent saved-output checks, native review
and complete102MP RGB16 exports are finished for both endpoints. Fine foliage,
neon detail and camera mottling remain weak; broad real-camera superiority
and100MP/10s remain goals. [GFX gallery](gfx-qualitative.md).

The [V116 data trial](fine-detail-data-training.md) has started after passing
its CUDA check. It tests fine weak sources and reviewed paired-reference masks
against completed Tiny V114. Its frozen parent/seed/budget and source/receipt
evidence remain intact. Trained quality is pending.

Earlier [V112 loss-scale results](v112-quality.md),
[V104 eight-view full panels](dihedral-quality.md), [V112 eight-view pilot](v112-eight-view.md),
[ADC sites option](adc-consistency.md) and [stronger RawNIND comparisons](rawnind-fullframe.md)
retain their explicit checkpoints and tradeoffs. Useful measured progress
updates the current guides without an old promotion gate.

| Topic | Start here |
| --- | --- |
| Current work | [V84-family cleaned-data/fine-detail training](quality-first-training.md) · [Completed loss-scale test](loss-scale-training.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V114, V115 and useful alternatives](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) · [Linear DNG/JPEG export](dng-export.md) |
| Data | [Reviewed90,864-source training corpus and native review](incoming-commons-quality.md), [prior Commons corpus](commons-post4557-reviewed.md), [source quality](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
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
