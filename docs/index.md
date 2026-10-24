# Documentation guide

Start with the [README](../README.md) for setup, inference and representative
native crops. **V112 final20k is the working quality baseline.** It reaches
36.90238dB on full427, +.10154dB over V104, with425 source means improving.
Known/unseen CFA means are54.26914/53.95378dB. Worst ADC flat bias falls to
50.89DN16 versus V104's1,218 and V111's2,143. [Complete review and native comparisons](v112-quality.md).

The [primary photo/camera comparison](v111-v112-primary-quality.md) and
[matched loss-scale trial](loss-scale-training.md) show V111-like photo quality,
higher V112 camera means and the repaired color tail. All seven matched panels
are complete; complete102MP exports and their167.51s FP32 observation are verified. Fine high-noise detail
and real foliage remain weak. [Current model choices](current-model.md).

The [larger-encoder work](small-aligned-training.md) is moving to V112. Its
V104-derived fit and eight CPU optimizer checks remain valid evidence, while
the idle V113 queue was superseded before any GPU work. Retained Small training
features/previews can support the new teacher fit without repeating the encoder
or source augmentation.

The [stronger RawNIND full-frame comparison](rawnind-fullframe.md) includes all
six native GFX regions and a separate ISO100 reference. Broad real-camera
superiority remains unachieved. The [V104 ADC sites option](adc-consistency.md)
and [eight-view V104 pilot](dihedral-quality.md) retain their explicit checkpoint
policies and tradeoffs; eight-view full-panel/export/audit work continues.
[Source review](incoming-commons-quality.md) and [fusion/transfer evidence](fusion-gate-quality.md)
remain available without freezing the current model choice.

| Topic | Start here |
| --- | --- |
| Current work | [V84-family cleaned-data/fine-detail training](quality-first-training.md) · [Completed loss-scale test](loss-scale-training.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V112 and useful alternatives](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
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
