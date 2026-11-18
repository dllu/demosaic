# Documentation guide

Reviewed November 17, 2026. **V120 Small is the general recommendation.**
Start with the [README](../README.md) for installation and inference.

## Current guidance

| Task | Start here |
| --- | --- |
| Choose a model or understand version numbers | [Model choices](current-model.md) |
| Run inference, set noise priors or export | [Usage](usage.md), [DNG/JPEG](dng-export.md), [hot pixels](hot-pixel-clusters.md) |
| Compare completed broad scores | [PSNR history through V131](performance-history.md), [V120 results](v120-v121-primary.md), [V131 results](v131-broad-primary.md) |
| Understand camera evidence and its gaps | [Real-camera overview](real-camera-quality.md) |
| Find active work and completed research outcomes | [Experiment index](experiments.md), [research priorities](research.md) |
| Understand the code and training data | [Architecture](architecture.md), [training pipeline](training-pipeline.md), [source review](current-source-loss-review.md) |
| Evaluate or publish a result | [Evaluation](evaluation.md), [documentation maintenance](documentation-maintenance.md) |
| Find files, caches and historical decisions | [Storage](storage.md), [diary](../diary/index.md) |

## Visual evidence

| Gallery/report | Actual coverage |
| --- | --- |
| [V120 primary crops and full-frame GFX](v120-v121-primary.md) | Recommended model; native synthetic GT and independent real references |
| [V131 endpoint](v131-endpoint-quality.md), [V132 endpoint](v132-endpoint-quality.md) | Completed 20k models; gains, regressions and both GFX families |
| [Main GFX scene](gfx-qualitative.md) | Links to current reviews plus checkpoint-specific historical gallery |
| [Fine green fence](gfx-green-mesh.md) | Links to latest fine/color studies plus historical gallery; separate ISO100 reference, not GT |
| [Q2/Sony/GFX50R](cross-camera-qualitative.md) | Historical V104/V114/V115 and RawNIND; no newer published gallery and no clean GT |
| [Material-detail gallery](heldout-detail.md) | Historical V112 and earlier comparisons; newer model reports linked at the top |
| [RawNIND variants](rawnind-variants.md) | Released-comparator definitions and historical matched studies |

## Detailed reviews and history

[Weak-detail literature](weak-detail-literature-2026-11.md) ·
[Global context and production review](weak-detail-global-context-production-review-2026-11-16.md) ·
[Training scale review](training-scale-pipeline-review-2026-11-17.md).

Implementation reports: [whole-scene context](whole-scene-context-next-test.md),
[expanded scene corpus](expanded-scene-corpus.md) ·
[matched2k native review](whole-scene-context-native-review.md) ·
[completed64-source/intervention study](whole-scene-context-development64.md) ·
[completed camera panels](whole-scene-context-camera-review.md) ·
[primary benchmark admission](whole-scene-context-primary-admission.md) ·
[full-corpus scaling](full-corpus-scaling.md) ·
[completed20k corpus review](full-corpus-control20k-review.md) ·
[long-schedule 20k native review](full-corpus-long20k-native.md) ·
[long-schedule 50k native review](full-corpus-long50k-native.md) ·
[long-schedule 86k native review](full-corpus-long86k-native.md) ·
[completed20k camera panels](full-corpus-control20k-camera-review.md) ·
[disjoint RAW direction guides](scene-wave-guides.md) ·
[phase profiles fitted from query RAW](guided-phase-profiles.md) ·
[discovery-only phase-fit shrinkage](guided-phase-fit-shrinkage.md) ·
[pooled RAW support under a quiet-error budget](fold-support-pooling.md) ·
[agreement between fitted RAW profiles](phase-profile-agreement.md) ·
[testing longer repeats in donor RAW](donor-subharmonics.md) ·
[oriented footprints for RAW validation](oriented-raw-support.md) ·
[joint Bayer phase-profile evidence](joint-phase-profile-support.md) ·
[donor-selected waveform harmonics](donor-phase-support.md) ·
[refitting RAW after held-out validation](phase-refit-delivery.md) ·
[fresh-geometry weighted refit test](fresh-phase-refit.md) ·
[bounded guide-error and recentering test](phase-guide-recenter.md) ·
[strong-edge exclusions for guide selection](phase-guide-edge-guard.md) ·
[shared waveform with signed Bayer amplitudes](shared-phase-shape.md) ·
[waveform shape from a disjoint RAW patch](donor-waveform.md) ·
[same-side RAW validation at strong edges](phase-edge-side.md) ·
[bright-side cross-edge evidence on fresh geometries](asymmetric-phase-evidence.md) ·
[RAW cross-check for donor frequency moves](phase-guide-crosscheck.md) ·
[RAW phase with changing wire geometry](phase-drift.md) ·
[measured phase geometry from a disjoint RAW donor](donor-phase-geometry.md) ·
[phase geometry fitted across opposing RAW donors](bracket-phase-geometry.md) ·
[screened search for RAW donor patches](search-donor-geometry.md) ·
[whole-frame scene context for donor selection](screened-scene-donors.md) ·
[appearance-first donor ranking and curved-wire recovery](affinity-first-donors.md) ·
[localized donor validation beside rails](localized-donor-validation.md) ·
[whole-frame ranking of localized RAW windows](scene-window-donors.md) ·
[query validation and two-boundary rail fits](query-rail-background.md) ·
[phase averages inside fitted surfaces](surface-phase-aggregation.md) ·
[signed local bounds for phase averaging](local-phase-bounds.md) ·
[curved boundaries for RAW validation](flexible-query-edges.md) ·
[nested screening for curved query boundaries](screened-query-edges.md) ·
[cross-color RAW validation for screened refits](cross-colour-refit.md) ·
[finite wire support beside rails](wire-envelopes.md) ·
[wire footprints from reserved RAW](reserved-wire-footprint.md) ·
[wire footprints with whole-image guide proposals](scene-wire-footprint.md) ·
[wider donor frequency banks](donor-frequency-bank.md) ·
[shared perspective for two wire directions](shared-projective-phase.md) ·
[narrow wire profiles inside measured footprints](finite-wire-profiles.md) ·
[companion frequency search inside a measured footprint](localized-guide-frequency.md) ·
[A-only innovation validation and native comparison](parent-innovation-validation.md) ·
[near and distant whole-scene context intervention](scene-context-extent.md) ·
[scene-conditioned RAW spectral gain](scene-spectral-detail.md) ·
[held-out gain calibration and proposal headroom](scene-spectral-gain-headroom.md) ·
[CUDA local-primary replay](local-primary-cuda-probe.md) ·
[complete588-color review](full-corpus-control20k-color-review.md) ·
[calibrated ADC-bin diagnostic](adc-bin-consistency.md) ·
[427-photo faint ADC comparison](full427-faint-adc.md) ·
[historical10k midpoint](full-corpus-control10k-review.md) ·
[execution/raw-EMA follow-up](training-execution-quality.md) ·
[qualified endpoint benchmark](full-corpus-primary-admission.md) ·
[CPU checkpoint recovery](full-corpus-checkpoint-cpu-recovery.md).

Individual experiment reports are evidence snapshots, not automatically current
recommendations. The [pre-cleanup entry points](history/before-2026-11-17-cleanup/README.md),
[archived research catalogue](history/before-2026-11-17-cleanup/research.md) and
[earlier experiment index](history/experiments-through-v200.md) preserve the long
history. Machine receipts and original comparison pixels remain unchanged.
