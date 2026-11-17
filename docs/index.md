# Documentation guide

Start with the [README](../README.md) for setup and full-frame inference,
[current model choices](current-model.md) for measured strengths and limits,
and [architecture](architecture.md) for the consolidated code and experiment
workflow. V120 Small remains the general recommendation.

| Task | Documentation |
| --- | --- |
| Run inference or export DNG/JPEG | [Usage](usage.md), [DNG export](dng-export.md) |
| Start or resume a configured experiment | [Current experiments](experiments.md), [architecture](architecture.md) |
| Understand broad training data | [Training pipeline](training-pipeline.md), [current source review](current-source-loss-review.md) |
| Evaluate restoration quality | [Evaluation](evaluation.md), [V120 results](v120-v121-primary.md) |
| Inspect latest detail/quiet tradeoffs | [Shared-edge](shared-edge-comparison.md), [three-noise finite wires](edge-snr-ladder.md), [V200](scale-supported-cfa-wave-comparison.md) |
| Follow the new carrier-allocation trial | [Proposal](competing-wave-candidates.md), [native review](competing-orientation-comparison.md), [conditional response](competing-edge-response.md): weak-direction gains with strong-direction losses |
| Follow the full-model comparison | [V131 completed control](v131-endpoint-quality.md); [V132 completed20k](v132-endpoint-quality.md): faint ADC −0.410 dB versus V131, ordinary tied, missing fine crossings. [Exact matched training](raw-spatial-continuation.md) and all native views complete |
| Inspect the remaining weak-response limit | [Coverage/response diagnostic](complementary-coverage-quality.md); [fixed-wave GT oracle](measured-wave-oracle.md): more response, persistent quiet/increment costs |
| Follow input-derived localization | [Completed full local/global panel](local-wave-full-panel.md): lower global-support error in all six cells; source-dependent weak gains and parent-error costs |
| Compare measurement averaging with waveform synthesis | [Phase aggregation](phase-measurement-aggregation.md): both projection arms complete; current400/far response12.68%, higher errors and persistent building bands |
| Inspect a richer withheld background | [A-only neural diagnostic](withheld-neural-background.md): better prediction of noisy building/cab sensor samples, still blurred/artifacted; no delivered restoration gain claimed |
| Test that background in a correction | [Whole-context neural nuisance](neural-nuisance-reconstruction.md): complete audited/native review; less added quiet/building error,400/far weak response3.69%→0.90%, missing cab crossings |
| Retain analytic proposals with that background | [Fixed-proposal neural nuisance](neural-nuisance-fixed-proposals.md): complete;2.69% weak response with quiet/increment RMS−0.574%/−0.133% versus3.686% analytic control; reduced building banding, zero neural replay |
| Check that operating point across the full panel | [Completed full neural-nuisance review](neural-nuisance-full-panel.md): quieter than analytic H1 in all6 cells;400/far weak2.299%, parent1.826%; slight parent-error costs, source1 dominance, all native views complete |
| Test larger context and complete edge coverage | [Native512 nuisance ablations](neural-nuisance-context512.md): far-background geometry fixed, weak response near-parent0.96%; native256 preferred; both audited/native reviews complete |
| Recover compact carrier proposals | [Hann512 physical discovery](neural-nuisance-hann512.md): weak response2.702%, increment error−0.093% versus parent; weaker strong response/higher full RGB error than256 neural, fine crossings absent; complete audited/native review |
| Localize carrier amplitudes | [Local129 amplitude ablation](spatial-carrier-amplitudes.md): weak response6.241% and lower increment error, severe new building bands; standalone conditional API reproduces both studies exactly |
| Keep background coefficients global | [Completed pilot](global-background-local-carriers.md); [completed full source/CFA/noise comparison](global-background-full-panel.md): versus256 NN, weak2.299%→2.778%, strong37.032%→48.055%, lower total RGB error and added cab ripple; higher quiet/increment errors, missing fine crossings;68 actual native figures |
| Reconstruct a richer measured wire profile | [Fixed-background phase reconstruction](global-background-phase-reconstruction.md): neural weak response27.390% on both reused sources, quiet/increment+2.352%/+0.434% versus parent; analytic increment−0.539% with severe real bands. Complete48-case/38-figure review; fine cab crossings unresolved |
| Restrict phase pooling to compatible signal levels | [Withheld neural guidance](neural-guided-phase-pooling.md) lowers pilot increment error/building bands. [Full eight-source review](neural-guided-phase-full-panel.md),70 actual figures:400/far analytic weak2.299%→9.300%, strong37.032%→68.274% versus256 NN, lower full RGB error; quiet/increment+0.258%/+0.606%, pilot increment gain does not persist; fine cab/high-noise recovery unresolved |
| Propose the missing fine-cab frequencies | [Additional fine band](fine-frequency-proposals.md): complete48-case/44-figure review; analytic1600/far weak0.989%→2.037%, same quiet/slightly lower increment error, source1-driven; cab lattice more visible with purple/green grid; building and neural1600 errors increase |
| Constrain the extra fine waveform | [Sinusoidal fine carriers](fine-sinusoidal-carriers.md): complete48-case/46-figure review; NN1600/far increment−3.017% versus fine phase with less response; cab grid persists/building bands increase; original broad diagnostics and fine geometry exact |
| Preserve colour through fine support | [Joint-colour support](joint-fine-colour-support.md): cab tint reduced with lattice retained, extra synthetic1600 response lost. [Fresh all-CFA coloured benchmark](coloured-fine-wire-benchmark.md),192 corrections/40 actual figures: small neutral weak gain, essentially no signed-colour weak gain and slightly worse signed increment/colour errors; no faithful crossing recovery |
| Supply whole-photograph context | [Scene-context next test](whole-scene-context-next-test.md): current DINO input remains tile-local. New CFA preview/native-coordinate feature-query utilities pass8 tests; source/header inventory exposes the missing shared scene/crop noise contract. No trained scene branch or quality gain yet |
| Validate the fine correction on an A-only neural base | [Parent-innovation control](parent-innovation-validation.md):114 regression tests; both48-case producers/numerical audits complete with0 new neural calls; actual native review and quality decision pending |
| Inspect waveform capacity and its cost | [Matching and harmonic follow-up](local-wave-shapes.md): more response, higher increment error and building bands; assignment fix retained |
| Inspect individual evidence and background | [Harmonic controls](individual-wave-validation.md): lower far error than group support, persistent real bands; [completed V131 broad review](v131-broad-primary.md): photo gain, unseen-camera/ADC-color costs |
| Use the fixed ADC repair | [V131 ADC Malvar](v131-adc-projection.md): ADC photo/color gains, weakest-band error cost; unchanged learned weights and positive-noise outputs |
| Follow the added-stage trial | [Complementary CFA branch](complementary-comparison.md): full review finds almost unchanged weak detail and slightly higher quiet/flat error; [fresh-noise follow-up](complementary-edge-response.md) retains a small lower-noise gain |
| Review literature and next weak-detail ideas | [November 2026 review](weak-detail-literature-2026-11.md), [withheld CFA](withheld-cfa-evidence.md), [edge refinement](withheld-cfa-edge-refinement.md) |
| Inspect real-camera weaknesses | [Main GFX scene](gfx-qualitative.md), [fine green mesh](gfx-green-mesh.md), [other cameras](cross-camera-qualitative.md) |
| Manage cached artifacts | [Storage](storage.md) |
| Understand historical decisions | [Diary](../diary/index.md), [experiment archive](history/experiments-through-v200.md) |

The pre-consolidation [model catalogue](history/current-model-through-v200.md),
[documentation guide](history/index-through-v200.md) and
[experiment index](history/experiments-through-v200.md) preserve all earlier
links and measured implementations. Running/queued descriptions in those
snapshots record their original writing context rather than current job state.
Machine receipts, frozen sources, checkpoint identities and historical artifact
paths are retained.
