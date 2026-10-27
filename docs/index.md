# Documentation guide

Start with the [README](../README.md) for setup, inference and representative
native crops. **V120 Small is the current general recommendation**, with
37.04008dB on full427 and54.31272/54.00872dB known/unseen measured-CFA means.
[Completed primary/local/native results](v120-v121-primary.md) document its
camera/color recovery and remaining weak-detail loss. V114 remains a useful
Tiny alternative; V115 has higher known-camera quality and V117 a slightly
higher photo mean. [Current choices](current-model.md).
The optional [V114 eight-view fixed24 comparison](v114-eight-view.md)
adds material/camera gains and native examples, with selected color-bias tradeoffs
and unmeasured complete-panel/frame scope.

V120's primary/analytic panels, independent saved-output checks, selected native
review, matched-profile GFX comparisons and complete102MP RGB16 exports are
finished. Fine foliage,
neon detail and camera mottling remain weak; broad real-camera superiority
and100MP/10s remain goals. [GFX gallery](gfx-qualitative.md).
The [completed V122/V12320k review](v122-v123-quality.md) records a small
joint-training photo gain over adapter-only training, with camera/color costs
and little weak-detail recovery. The [V12414k progress review](v124-progress14000.md)
adds noisy/shadow gains of.008–.033dB, faint ADC−.350dB and native material/GFX
crops without clear mesh recovery. Its original20k control is complete; V125
awaits its declared headroom and full endpoint quality is pending. V120 remains
the general choice.

The [completed V116 data comparison](v116-quality.md) raises tested eight-pixel
weak-carrier gain, but does not improve broad weak natural detail and worsens
the ADC color tail. Complete metrics, native triplets, six GFX regions and RGB16
checks are published. V114 retains the better balance within that Tiny comparison.

The [completed V117/V118 comparison](v117-v118-quality.md) adds a useful V117
single-view photo option at37.04408dB, with slightly lower camera means and
higher ADC bias than V114. The matched band term lowers weak natural-detail
response and raises worst ADC bias to843.05DN16. Complete independent metrics,
native triplets/six GFX regions and full RGB16 checks are published.

Earlier [V112 loss-scale results](v112-quality.md),
[V104 eight-view full panels](dihedral-quality.md), [V112 eight-view pilot](v112-eight-view.md),
[ADC sites option](adc-consistency.md) and [stronger RawNIND comparisons](rawnind-fullframe.md)
retain their explicit checkpoints and tradeoffs. Useful measured progress
updates the current guides without an old promotion gate.

| Topic | Start here |
| --- | --- |
| Current work | [V129 curated-detail data trial](reviewed-detail-training-pilot.md) · [Completed V128 feature pilot](v128-feature-pilot-quality.md) · [Completed V126/V127 shadow pilot](reviewed-shadow-pilot-quality.md) · [V123 saved-state recovery](v123-memory-guard-recovery.md) · [V124/V125 conditional-mean training](conditional-mean-training.md) · [V122/V123 learned frequency trials](learned-raw-frequency-training.md) · [Native-camera comparison](native-camera-development.md) · [Current model choices](current-model.md) |
| Results | [Experiment index](experiments.md), [PSNR history](performance-history.md) |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V120 and useful alternatives](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) · [Linear DNG/JPEG export](dng-export.md) |
| Data | [Current Small-model source inspection](current-source-loss-review.md), [actual target contrast coverage](training-target-contrast-coverage.md), [reviewed-material shadow exposure](reviewed-shadow-exposure.md), [paired32/weak-detail trials](paired32-weak-detail-training.md), [native camera development inputs](native-camera-development.md), [corpus and native review](incoming-commons-quality.md), [paired camera sampler](paired-camera-sampling.md), [source quality](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
| Training | [Current quality work](quality-first-training.md), [spatial trial and early progress review](raw-spatial-training.md), [data/augmentation pipeline](training-pipeline.md), [execution/restart](training-execution.md), [mean-loss training](conditional-mean-training.md), [earlier engineering evidence](quality-training-validation.md) |
| Evaluation | [Current endpoint review queues](endpoint-quality-review.md), [quality/noise diagnostics](evaluation.md), [natural fine detail](heldout-detail.md), [conditional-noise bias](conditional-noise-response.md), [loss-gradient replay](conditional-loss-gradients.md), [RawNIND variants](rawnind-variants.md), [noise/detail tradeoff](noise-conditioning.md), [ADC-only consistency](adc-consistency.md), [V104 color/texture projection diagnostics](v104-adc-color-projection.md), [GFX test](gfx-qualitative.md), [prepared test reserve](paired-reserved-test.md) |
| Method research | [Current research](research.md), [RAW spatial features](raw-spatial-features.md), [learned RAW frequency prototype](learned-raw-frequency-features.md), [measured green-phase mesh diagnostic](green-phase-spectrum.md) |
| Completed global-attention pilot | [V136 matched1k quality and native crops](v136-global-attention-quality.md): tiny gains over V129, mixed local detail, no clear new mesh recovery. [Operator and genuine checks](raw-global-attention.md); V120 remains the general choice |
| Completed global-conditioning pilot | [V137 measured quality, native triplets and both GFX pairs](v137-global-conditioned-quality.md): stronger memory adaptation, faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and no clear new fine-mesh recovery. [Operator and mechanism](raw-global-conditioning.md) |
| Global-branch training | [V138 frozen-parent pilot](raw-global-only-training.md): CPU/CUDA16+2 checks pass with91 parent model/EMA tensors exact. Larger branch LR and1k quality review are queued after V125 completes; quality is unmeasured |
| Remaining requirements | [Current completion checklist](requirements.md), [historical progress log](requirements-archive.md) |

Per-experiment reports contain numerical evidence, source/ROI metadata,
checkpoint hashes, noise/display settings and native triplets. Study-specific
eligibility gates do not prevent showing useful versions or changing the current
baseline. References and decisions inside a versioned report apply to that
study; follow [current model choices](current-model.md) for today's recommendations.
Timestamped historical decisions belong in the diary. Real low-ISO or
independently demosaiced references are labeled accurately. Machine receipts
retain recorded UTC timestamps; diary filenames use America/Los_Angeles time.
