# Current model choices

Reviewed November 17, 2026. **V120 Small is the general inference recommendation.**
The latest completed broad comparison is V131; its higher photo score comes with
camera and color costs. The [completed64-source scene review](whole-scene-context-development64.md)
finds small quiet-region gains and mixed detail/color costs; fine crossings
remain missing. The [completed camera panels](whole-scene-context-camera-review.md)
find a partial unseen-camera repair over local-only, still below V120.
Full427 photo evaluation is running.
A [100k full-corpus V120 continuation](full-corpus-scaling.md)
has completed its first1,000 updates and awaits its scheduled continuation after
the running20k control. The [control10k midpoint](full-corpus-control10k-review.md)
has53,506 source IDs visited, but faint fidelity−0.61431 dB and no convincing new
fence crossings. Both fence families were viewed; scaling endpoint broad scores
remain pending.
The [raw/EMA follow-up](training-execution-quality.md) finds10k raw worse than
EMA on all three review means. The control has actually covered all90,778
photos; its [endpoint benchmark](full-corpus-primary-admission.md) is queued.
[Research status](experiments.md).

## Full-model choices

| Model | Useful result | Limits and intended use |
| --- | --- | --- |
| **[V120 Small](v120-v121-primary.md)** | 37.04008 dB on 427 photos; known/unseen measured-CFA means 54.31272/54.00872 dB; verified 102MP RGB16 export | General choice. Fine mesh, foliage, neon and dark-field mottle remain weak; the 10-second target is unmet |
| [V131 continuation](v131-broad-primary.md) | 37.08008 dB on the same photo panel; 400/427 source means improve; targeted faint ADC +0.14555 dB over V120 | Experimental photo/detail option. Unseen-camera −0.04381 dB; worst ADC mean-color error 1,816 DN16 versus V120's 55.5; no new full-frame validation |
| [V131 ADC Malvar](v131-adc-projection.md) | Same learned weights; ADC-only photo +0.15074 dB over V131 and worst ADC color error reduced to 19.98 DN16 | Opt-in repair for zero shot/read conditioning. Weakest ADC band error +1.43%; positive-noise V131 output and camera costs remain unchanged |
| [V132 RAW attention](v132-endpoint-quality.md) | Completed 20k ablation with every training input hash matched to V131 | Faint ADC −0.40978 dB versus V131, ordinary material quality essentially tied; no broad-panel or full-frame validation. Retained for reproduction |
| [Scene-context2k arms](whole-scene-context-camera-review.md) | Scene/tile API;64-source quiet-coarse gains. Spatial unseen-camera +0.01739 dB versus matched local-only; pooled provides almost the same repair | Unseen remains−0.05477 dB versus V120; known nearly ties local-only. No established weak-detail gain or faithful new fence crossings; original local encoder retained. Full427 photos running |
| [Corpus control10k midpoint](full-corpus-control10k-review.md) | Broader actual source coverage; selected ADC flat mean bias15.08→7.87 DN16 | Faint ADC−0.61431 dB; selected flat centered RMS4.64→8.69 DN16; no convincing new crossings. Midpoint only,20k/100k and broad panels pending |

V131's broad mean, the four-source faint-detail means, and ADC-only photo means
are different measurements. The [PSNR history](performance-history.md) includes
only comparable completed broad panels. A higher mean score alone does not
establish better weak-detail recovery or cleaner flat regions.

Earlier measured alternatives remain documented: [V114/V115](v114-v115-quality.md)
and [V117/V118](v117-v118-quality.md). Their individual strengths do not make the
largest experiment number the recommended model.

## Loading and inference

Use the [README command](../README.md#setup-and-inference) for full-frame inference.
`demosaic-experiment models` lists available presets;
`demosaic.models.registry.load_model("v120")` verifies its declared checkpoint.
The `v131`, `v131-adc-malvar` and `v132` presets preserve the reviewed variants.
Checkpoint hashes, configuration, source/ROI and noise/display provenance are
in each linked report. [Package interfaces](architecture.md).

## Experimental detail components

These are useful, bounded tradeoffs, not a general replacement for V120:

| Component family | What worked | What remains unresolved |
| --- | --- | --- |
| [V187/V195/V198/V200 wave heads](scale-supported-cfa-wave-comparison.md) | V198 EMA reaches 11.158% of constructed-GT mesh amplitude; V200 slightly reduces quiet/flat error at 11.102% response; V187 is quieter and V195 avoids the new building fringes | Incomplete crossings, false texture and green/magenta building fringes. Amplitude response is not overall accuracy |
| [Local support and neural nuisance](neural-nuisance-full-panel.md) | Lower added quiet/increment error than analytic local waves and smaller building bands | Much weak detail remains absent; errors still slightly above the parent |
| [Guided phase, full panel](neural-guided-phase-full-panel.md) | At the clearest far-edge condition, weak response 2.299%→9.300% versus the 256-context neural control; lower full RGB error | Quiet/increment error +0.258%/+0.606%; the two-source pilot's increment gain did not persist |
| [Fine-band joint color support](joint-fine-colour-support.md) | More visible cab lattice with reduced purple/green tint versus independent support | Building bands remain; the [fresh colored-wire test](coloured-fine-wire-benchmark.md) finds essentially no signed-color weak gain and higher increment/color errors |
| [Supported-amplitude inference stage](supported-wave-amplitude.md) | More mesh contrast within measured reciprocal support | Higher blank-region RMS, seams and spill; opt-in only, with cost separate from the base model |

V187/V195/V198/V200 component loaders require base RGB and physical RAW inputs;
the component exports alone are not full-frame parent models. Other composed
stages have their own teacher/context requirements. Read the report and
[architecture interfaces](architecture.md) before selecting one.

## Version numbers and evidence coverage

V-numbers are experiment identifiers assigned when work is started. Separate
branches can finish out of order: V131/V132 are full-model continuations from
V120; later-numbered wave heads train small components over frozen parents.
They do not form one release sequence or one continuous training run.

The [real-camera overview](real-camera-quality.md) distinguishes scored panels
from unscored galleries. The Q2/Sony/GFX50R gallery still ends at V114/V115;
newer GFX reviews do not fill that camera-coverage gap. Independent low-ISO
captures differ in aperture, exposure and motion and are not exact RGB GT.

[Active research and grouped results](experiments.md) ·
[Detailed choices before this cleanup](history/before-2026-11-17-cleanup/current-model.md) ·
[Earlier V200-era catalogue](history/current-model-through-v200.md).
