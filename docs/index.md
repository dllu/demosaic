# Documentation guide

The [V146 Fourier and mesh pilot](v146-coherent-frequency.md) completes
500 updates with the V143 parent frozen, followed by both raw and EMA reviews on 694
inputs each. Mesh response grows less than .7% relative while mesh/photo errors rise; 22 inspected
native figures show no useful new lattice. Small flat/sky gains do not change
the useful baselines. Window metadata and resume checks now preserve geometry.
Its [matched inference-window follow-up](v146-window-transfer.md) also finds no
useful recovery at native512 support with the same weights. 32 native figures and
72 fresh512 flat fields are complete; smaller-context bypasses are explicit.

The new [supported-amplitude option](supported-wave-amplitude.md) keeps the
original positive global gate as selection and restores contrast only inside
unchanged reciprocal support. Fresh mesh response rises 26.4% and image RMS
falls 1.0% versus cross; mean/worst added blank RMS rise 42.1%/28.4%. All 256 absent
cases and 64 new photographic controls retain their parents. Full GFX mesh
contrast improves under both priors; nonperiodic texture, support seams, boundary
spill and highlight color remain unresolved. The explicit `detail` mode has
53 inspected native comparisons and complete RGB16 checks. V120 remains the general model recommendation. Detail is now the default
inside the explicitly enabled periodic stage.

The earlier [reciprocal green-support review](cross-phase-support.md) cuts fresh mean
added blank RMS 89% and its worst case 92% versus wide context, with 9.5% lower
response and 0.8% higher image RMS. Both full-frame mesh priors retain much of the
lattice. The known detached false patch is removed; weak/partial detail and
boundary spill remain. All 256 fresh absent neural cases retain parent values.
The explicit `cross` mode has 37 viewed native comparisons and complete RGB16
audits; it is a stricter support option, not a broad model-quality claim.

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

The [guarded wider-context option](wide-phase-context.md) adds stronger measured
lattice detail on complete V143 frames. Fresh response improves 14.4% and image
RMS 1.2% versus sparse support; mean blank spill rises 17.3% and its worst case
falls 17.4%. The tested sky, 256 absent neural cases and 5,120 matched/mismatch flat
executions retain all parent pixels. The amplified tail still has a detached
false stripe patch. The explicit `wide` mode includes 31 viewed native boards,
fresh GT triplets, failure controls and complete RGB16 audits.

The additional [connected support/refit mode](sparse-phase-support.md) strengthens
the real lattice on complete V143 frames. Final fresh validation gives 12.8% more
response and 34.0% less mean added blank RMS versus refined TV, with 39.2% higher
worst-case blank RMS. The known isolated stripe island is removed; connected
boundary leakage remains. Wider sky and all 256 final absent inputs stay unchanged.
This remains opt-in; Detail is the current default inside the enabled stage.

The later [direct RAW refit study](raw-phase-refit.md) finds a small spill/detail
tradeoff on another 64 fresh recipes: 7.7% less mean blank spill, 0.5% lower
response and slightly higher image error. Boundary continuation and coarse-solver
caps remain. It is retained as a research tool with matched native comparisons.

The earlier [continuous-frequency TV fit](offgrid-phase.md) gives modest,
placement-sensitive mesh changes on complete 102MP RGB16 outputs. Fresh 64-recipe validation
finds 3.7% more response and slightly lower texture error versus fixed-bin TV,
with 8.5% higher added blank RMS. Wider sky, all 256 absent inputs and 4,096 fresh
flat-selector cases bypass. Highlight color, spill, window sensitivity and speed
remain open. [Fixed-bin TV](edge-phase-envelope.md) remains explicitly available.
[Earlier complex fit](complex-phase-envelope.md) · [Scalar implementation](phase-harmonic-inference.md).

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
stopped at the memory reserve. The [V1252k review](v125-progress2000-quality.md) records a better
eight-photo monitor, mainly highlights, with weaker faint texture on separate
support and no clear new mesh recovery. Full endpoint quality is pending. V120 remains
the general choice.

The [complete V1401k review](v140-standalone-pilot.md) executes the checked
patch-memory recipe after the original dependency chain exited. Its102-input
matched native/GFX review and48 exact-flat checks find near-V120 quality,
without clear new mesh recovery. Old failure receipts and partial checkpoints remain
intact.

The [completed V142 data-only review](v142-crossed-line-pilot.md) adds.05212dB
faint ADC PSNR and4.55% lower noisy-flat spatial RMS versus matched V129. Its
[crossed-line/empty data](crossed-line-training-data.md) stays useful for further
quality trials. Real mesh shows no clear new recovery; coarse noisy-flat error
is5.08% above V120 and selected ADC-only color bias worsens. Native triplets,
both GFX pairs, exact flats and fixed input-selected mesh peaks are published.

The [V143 combined data/gradient5k candidate](v143-crossed-gradient5000.md) has
[completed its 5k native/faint/GFX/48-flat review](v143-final5000-quality.md):
faint ADC gains .26493dB versus V120 with coarse-noise and ADC-flat costs.
Full427/camera quality remains unmeasured; V120 stays the general recommendation.

The [completed V141 small-gradient-loss pilot](v141-gradient-epsilon-pilot.md)
recovers.01528dB faint ADC PSNR over matched V129, with mixed local-band changes
and no new real-mesh recovery. Its48 exact-flat observations and added V129
controls show about5.8% more coarse noisy-flat error than V120 in both
continuations. Native triplets, both GFX pairs and independent audits are published.

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
| Latest source review | [V131 high-loss inspection](v131-source-review.md):40 new sources, two future-only exclusions and one mixed white-plumage context; prepared90,774/36, trained quality unmeasured |
| Older work | [Chronological archive](experiment-archive.md), [local-time diary](../diary/index.md) |
| Current model | [V120 and useful alternatives](current-model.md) · [Real-camera metrics](real-camera-quality.md) · [GFX comparisons](gfx-qualitative.md) · [Q2/Sony/GFX50R](cross-camera-qualitative.md) |
| Usage | [Commands and data conventions](usage.md) · [Linear DNG/JPEG export](dng-export.md) |
| Data | [Current Small-model source inspection](current-source-loss-review.md), [actual target contrast coverage](training-target-contrast-coverage.md), [reviewed-material shadow exposure](reviewed-shadow-exposure.md), [paired32/weak-detail trials](paired32-weak-detail-training.md), [native camera development inputs](native-camera-development.md), [corpus and native review](incoming-commons-quality.md), [paired camera sampler](paired-camera-sampling.md), [source quality](corpus-source-review.md), [source exclusions](commons-content-overlap.md), [native RAW targets](public-raw-expansion-v2.md) |
| Training | [Current quality work](quality-first-training.md), [spatial trial and early progress review](raw-spatial-training.md), [data/augmentation pipeline](training-pipeline.md), [execution/restart](training-execution.md), [mean-loss training](conditional-mean-training.md), [earlier engineering evidence](quality-training-validation.md) |
| Evaluation | [Current endpoint review queues](endpoint-quality-review.md), [quality/noise diagnostics](evaluation.md), [natural fine detail](heldout-detail.md), [conditional-noise bias](conditional-noise-response.md), [loss-gradient replay](conditional-loss-gradients.md), [RawNIND variants](rawnind-variants.md), [noise/detail tradeoff](noise-conditioning.md), [ADC-only consistency](adc-consistency.md), [V104 color/texture projection diagnostics](v104-adc-color-projection.md), [GFX test](gfx-qualitative.md), [prepared test reserve](paired-reserved-test.md) |
| Method research | [Current research](research.md), [RAW spatial features](raw-spatial-features.md), [learned RAW frequency prototype](learned-raw-frequency-features.md), [measured green-phase mesh diagnostic](green-phase-spectrum.md) |
| Completed global-attention pilot | [V136 matched1k quality and native crops](v136-global-attention-quality.md): tiny gains over V129, mixed local detail, no clear new mesh recovery. [Operator and genuine checks](raw-global-attention.md); V120 remains the general choice |
| Spatial-trial control progress | [V131 retained1k/20k review](v131-progress1000-quality.md): tiny ordinary gain, deeper-shadow/faint regressions and no clear new mesh recovery; native triplets, both GFX pairs and corrected DSCF3835 camera-JPEG comparisons. Original20k worker stopped at the memory reserve; V132 production unstarted |
| Completed global-conditioning pilot | [V137 measured quality, native triplets and both GFX pairs](v137-global-conditioned-quality.md): stronger memory adaptation, faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and no clear new fine-mesh recovery. [Operator and mechanism](raw-global-conditioning.md) |
| Global-branch training | [Completed V1381k](v138-quality.md): all 91 parent model/EMA tensors stay exact; faint ADC +.00406 dB and noisy-flat spatial RMS −.15% versus V120, without clear new mesh recovery. All 150 review inputs, audits and native viewing complete |
| Trained global-memory contribution | [V137 feature-level ablation](global-memory-contribution.md): removing memory write changes0.83–1.39% of branch-offset RMS on six contexts. Independent attention/array audit complete; V138 image review is complete; the original same-input mechanism companion remains unmeasured |
| Mean-loss progress | [V125 at2k](v125-progress2000-quality.md): highlight-dominated eight-photo monitor gain over V1242k, weaker faint texture versus V120, and no clear new mesh recovery. Native GT triplets, both GFX pairs and corrected DSCF3835 camera JPEGs published; original20k comparison remains incomplete after the memory-reserve stop |
| Memory-only global branch | [V139 implementation and queued pilot](raw-global-memory-only.md): CPU/CUDA16+2 checks pass; original dependency queue exited;1k training and matched native/faint/GFX review remain prepared, with510 controls reusable. Image quality remains unmeasured |
| Remaining requirements | [Current completion checklist](requirements.md), [historical progress log](requirements-archive.md) |

Per-experiment reports contain numerical evidence, source/ROI metadata,
checkpoint hashes, noise/display settings and native triplets. Study-specific
eligibility gates do not prevent showing useful versions or changing the current
baseline. References and decisions inside a versioned report apply to that
study; follow [current model choices](current-model.md) for today's recommendations.
Timestamped historical decisions belong in the diary. Real low-ISO or
independently demosaiced references are labeled accurately. Machine receipts
retain recorded UTC timestamps; diary filenames use America/Los_Angeles time.
