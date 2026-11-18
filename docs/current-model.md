# Current model choices

Reviewed November 17, 2026. **V120 Small is the general inference recommendation.**
The latest completed broad comparison is V131; its higher photo score comes with
camera and color costs. The [completed64-source scene review](whole-scene-context-development64.md)
finds small quiet-region gains and mixed detail/color costs; fine crossings
remain missing. The [completed camera panels](whole-scene-context-camera-review.md)
find a partial unseen-camera repair over local-only, still below V120.
Full427 photo evaluation is running.
The [completed full-corpus20k control](full-corpus-control20k-review.md) has
actually visited all90,778 photos. Faint mean recovers0.59370 dB from10k,
remaining0.02061 dB below V120; ordinary/shadow gains are small and three faint
materials have higher fine-band error. Both real fence families were viewed
without convincing new crossings. The original 100k trajectory's
[matched 20k review](full-corpus-long20k-native.md) improves faint
fine-band error on bark, fur, and wood while losing mean faint sRGB PSNR
against the short schedule.
The20k control's [full427 benchmark](full-corpus-primary-admission.md) is running. The
[completed camera panels](full-corpus-control20k-camera-review.md) gain0.03285 dB
known and lose0.04067 unseen versus V120, with mostly channel-mean unseen costs.
The [complete ADC-color panel](full-corpus-control20k-color-review.md) exposes
worst raw mean bias765.7 DN16 versus V12055.5; physical corrections repair most
of it. These costs keep the completed control experimental.
[Research status](experiments.md).

## Full-model choices

| Model | Useful result | Limits and intended use |
| --- | --- | --- |
| **[V120 Small](v120-v121-primary.md)** | 37.04008 dB on 427 photos; known/unseen measured-CFA means 54.31272/54.00872 dB; verified 102MP RGB16 export | General choice. Fine mesh, foliage, neon and dark-field mottle remain weak; the 10-second target is unmet |
| [V131 continuation](v131-broad-primary.md) | 37.08008 dB on the same photo panel; 400/427 source means improve; targeted faint ADC +0.14555 dB over V120 | Experimental photo/detail option. Unseen-camera −0.04381 dB; worst ADC mean-color error 1,816 DN16 versus V120's 55.5; no new full-frame validation |
| [V131 ADC Malvar](v131-adc-projection.md) | Same learned weights; ADC-only photo +0.15074 dB over V131 and worst ADC color error reduced to 19.98 DN16 | Opt-in repair for zero shot/read conditioning. Weakest ADC band error +1.43%; positive-noise V131 output and camera costs remain unchanged |
| [V132 RAW attention](v132-endpoint-quality.md) | Completed 20k ablation with every training input hash matched to V131 | Faint ADC −0.40978 dB versus V131, ordinary material quality essentially tied; no broad-panel or full-frame validation. Retained for reproduction |
| [Scene-context2k arms](whole-scene-context-camera-review.md) | Scene/tile API, 64-source quiet-coarse gains. Spatial unseen-camera +0.01739 dB versus matched local-only. [Distant context changes foliage and coarse-fence output](scene-context-extent.md) | Unseen −0.05477 dB versus V120, known nearly ties local-only. Fine crossings remain incomplete. Full427 photos running |
| [Corpus control20k](full-corpus-control20k-review.md) | Completed320k target slots/all90,778 photos. Ordinary/shadow +0.00852/+0.01047 dB; substantial faint recovery from10k | Faint−0.02061 dB versus V120; fine-band error higher for3/4 materials, selected flat spatial RMS worse. Known/unseen +0.03285/−0.04067 dB; worst ADC mean error765.7 versus55.5 DN16. [Camera](full-corpus-control20k-camera-review.md)/[color](full-corpus-control20k-color-review.md) reviews complete, no faithful new fence crossings; full427 photos collecting |
| [Long schedule at 20k](full-corpus-long20k-native.md) | Fine-band RMS improves for bark, fur, and wood against both V120 and short 20k; faint camera-RGB PSNR is +0.15853 dB over short | Rendered faint PSNR is −0.19124 dB versus short. Grass, flat spot checks, and fine cab crossings remain weak. This checkpoint has a scoped native review |
| [Long schedule at 50k](full-corpus-long50k-native.md) | Retained ordinary and shadow sRGB are +0.020/+0.044 dB over V120 | Faint fine-band RMS rises on all four materials versus V120. Bright orange ADC mean error reaches 1,490 DN16 in a BGGR spot check, with visible unevenness. Fine cab crossings still incomplete |

The [calibrated ADC follow-up](full-corpus-long50k-native.md#calibrated-adc-follow-up)
reduces the 50k worst spot-check bias to 11.16 DN16 and improves faint
sRGB. Compared with V120 using the same projection, 50k still has
higher mean fine-band RMS and higher flat bias.

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

The disjoint RAW direction-guide probe improves lower-noise synthetic
far-wire response with a small reduction in increment error. The real cab
tradeoff and near-edge costs keep it experimental. A phase-bin fit sharpens
some lower-noise synthetic wires compared with the sinusoid and lowers their
paired increment error. Discovery-only shrinkage reduces excess quiet error
at the permissive ISO6400 setting while attenuating wire response too.
ISO6400 weak recovery at conservative settings and real cab crossings
remain open. [Direction-guide review](scene-wave-guides.md) ·
[Phase-profile results](guided-phase-profiles.md) · [Shrinkage results](guided-phase-fit-shrinkage.md).

Pooling positive evidence from both RAW folds raises held-out ISO400 far
weak response from 14.19% to 16.89% at nearly equal mean quiet error.
ISO6400 gains are smaller and have mixed increment errors. Both standing
families retain the same remaining fine-detail limitations.
[Pooled support and native crops](fold-support-pooling.md).

A phase-agreement weight further reduces the small building correction
from 0.421 to 0.166 DN16 RMS. It lowers weak response in all four
noise and edge cells at the tightest quiet budget. The ISO6400 far
weak fits show similar agreement when the wire is present or absent.
[Agreement results](phase-profile-agreement.md).

The [donor subharmonic check](donor-subharmonics.md) repairs two doubled
frequencies. At the same quiet error, it raises held-out ISO400 far weak
response from 16.89% to 17.54%. The tighter ISO6400 gate still recovers
little weak detail, and real cab crossings remain unresolved.

The [oriented-support comparison](oriented-raw-support.md) favors the
square validation window at the tight quiet budget. Both tested
rectangles lose low-noise recovery. At ISO6400 far they slightly reduce
increment error and also reduce weak response.

The [joint Bayer phase-profile test](joint-phase-profile-support.md)
finds smaller far-edge weak response when sharing evidence across
colors at the tight quiet budget. The near-edge ISO400 response
improves slightly with higher increment error. The sky matches V120
and the fine cab crossings remain unresolved.

The [donor waveform comparison](donor-phase-support.md) retains more
weak response with the full eight-knot basis at all three calibrated
budgets. Selecting higher harmonics with an external RAW region keeps
most of that response and slightly lowers ISO6400 increment error at the
tight budget. A fundamental-only fit loses much more signal.

The [weighted RAW refit](phase-refit-delivery.md) improves ISO400
far-edge weak response from 17.54% to 21.07% at the tight calibration
budget, with lower increment error and slightly higher quiet RMS.
It reaches 19.16% at equal measured quiet RMS in a separate
diagnostic. Uniform refitting changes little, and the weighted
ISO6400 near and real cab results remain limited.

The [fresh refit panel](fresh-phase-refit.md) confirms the ISO400 far
gain on eight new geometries with accurately measured guides. Frozen
settings give 20.94% fold-average and 23.66% weighted response at
virtually the same quiet RMS. Both exceed the intended absolute quiet
budget. The ISO6400 gain is limited and the camera comparison uses
the same reviewed refits.

The [bounded guide search](phase-guide-recenter.md) recovers 22.33%
of the ISO400 far weak increment after a one-bin radial error,
compared with 1.36% from the shifted guide alone. It lowers recovery
with the nominal near-edge guides and offers little repair at
ISO6400. The fine cab crossings remain unresolved.

An [8-pixel edge exclusion](phase-guide-edge-guard.md) raises ISO400
near-edge weak response from 6.47% to 12.16% with nominal
guides while preserving the far-edge radial repair. The guard changes
frequency selection only, with a small measured quiet-error increase
on the near-edge fields.

The [shared waveform fit](shared-phase-shape.md) slightly lowers
far-edge chroma error but weakens near-edge recovery. At the same
measured quiet RMS, ISO400 near gives 12.00% weak response with
independent waveforms and 7.65% with one shared shape.

A [disjoint-donor waveform](donor-waveform.md) gives a small
far-edge increment and chroma error reduction. Near-edge ISO400
response at matched quiet RMS falls from 12.16% to 7.54%.
The real fine cab crossings remain incomplete.

[Same-side validation](phase-edge-side.md) improves ISO400
dark-side weak recovery from 8.19% to 11.84% at equal measured
quiet RMS. Bright-side recovery falls from 6.87% to 5.22%.
Separate profiles lose more overall response, and the real
fine cab views retain the guarded fit.

On [new wire geometries](asymmetric-phase-evidence.md), cross-edge
evidence lowers the ISO400 near-edge response compared with same-side
validation at matched quiet RMS. Holding the accurate donor frequencies
fixed raises recovery from 3.94% to 6.12% with lower increment error.
That fixed-guide replay covers ISO400 near scenes.

The [RAW frequency cross-check](phase-guide-crosscheck.md) tests proposed guide
moves on two disjoint discovery subsets before separate confirmation. At matched
quiet error, ISO400 near-edge recovery rises from 3.94% to 4.35% with nominal
guides. Far-edge recovery falls from 22.33% to 19.92% with shifted guides.
The real cab mesh remains incomplete.

The [RAW phase-drift search](phase-drift.md) lowers ISO400 far weak response
at the same quiet error and leaves both real fences unchanged. Exact
geometry helps a smaller lower-noise far-edge diagnostic, pointing to
geometry estimation on stronger measurements as a possible next step.
The [measured donor test](donor-phase-geometry.md) gives a small gain
on the lower-noise far curved subset with the same fixed planar
center frequencies. All reviewed GFX queries use the guarded fallback.
The [opposing-donor comparison](bracket-phase-geometry.md) gives stronger
ISO400 far weak response with matched quiet error. The ISO6400 far
weak-increment error rises slightly, and the visible cab crossings
remain incomplete.

[Searching surrounding RAW](search-donor-geometry.md) improves straight-wire
response at ISO400 far and loses most of the fixed donor result on curved
wires. It preserves the sky and reduces added cab banding toward V120.
The selected cab donors support coarse structure, and fine crossings
remain incomplete.

[Whole-frame context for donor ranking](screened-scene-donors.md)
produces the same synthetic outputs as near-context ranking. The
two left cab brackets shift toward more visible mesh on one side, with
the train body on the other side and fine crossings still missing.
The synthetic affinity ranks suggest a stronger role for context
in pair selection before query-local RAW validation.

[Appearance-first ranking](affinity-first-donors.md) modestly improves
matched-quiet recovery on fresh ISO400 fields with distinct paints.
The same-paint cases show negligible recovery. A wider second-family
search helps a retained curved subset and leaves the real outputs exact.
The cab has more plausible donor choices with missing fine crossings,
and a fallback can reintroduce banding.

[Localized donor validation](localized-donor-validation.md) uses a
two-boundary background fit that reduces rail-only false guide acceptance
from 23/24 to 2/24 while preserving the refined fit's synthetic wire
response. V120 fallback removes diagonal cab banding when donor
validation fails. The fine crossings remain incomplete and ISO6400
faint-wire response is below 1% on the occlusion replay.

[Whole-frame ranking of localized RAW windows](scene-window-donors.md)
recovers 4.80% of the faint ISO400 wire increment within the declared
quiet allowance, versus 0.89% for spectral ranking and 9.02% with
fixed brackets. At V143's quiet RMS, near and full-frame ranking
both recover less than 1%. Full-frame ranking avoids visible building
bands introduced by the wider spectral search. The cab crossings
remain soft.

[Two-boundary query validation](query-rail-background.md) lowers
rail-only correction RMS from 7.29 to 0.79 DN16 with forced guides
and retains about 4.80% ISO400 weak response with full-frame guides
at the same quiet limit. It suppresses the building's color bands
when the spectral guide is held fixed. The finer cab mesh still
falls back to V120, and removing the held-out amplitude penalty
weakens recovery at matched quiet error.

[Surface-constrained phase averaging](surface-phase-aggregation.md)
uses the existing wave gate and a per-color energy cap. ISO400 weak
response rises from 4.80% to 5.03% on the main panel and from 6.44%
to 6.98% on separate geometries, with lower quiet RMS in both.
Increment error changes only slightly. Forced-guide rail peaks rise
despite similar RMS, and the fine cab mesh remains unresolved.

[Local bounds on phase averaging](local-phase-bounds.md) remove
the large peaks from whole-query energy scaling. The signed peak
bound retains most of the small ISO400 response gain on both
geometry sets, with greater RMS on the fresh rail controls.
Bounding local energy lowers rail RMS and peaks with weaker
wire recovery. Both variants return the fine cab crops to V120.

[Flexible query boundaries](flexible-query-edges.md) reduce forced-guide
complex rail RMS from 5.16 to 0.97 DN16 with up to four boundaries.
They slightly weaken response on the main ISO400 wire panel,
increase errors on the straight controls and recover little of
the faint signal deliberately added beside rails. The fine cab
crossings remain incomplete.

[Nested RAW background screening](screened-query-edges.md) retains
the curved fit's reduction on the new complex rail controls, from
5.61 to 1.31 DN16 RMS over parallel steps. It retains the parallel
refit's predictions on the archived positive panels and cuts the
unscreened straight-edge error. Fine crossing recovery beside rails
remains negligible.

The opt-in [ADC-bin helper](adc-bin-consistency.md) improves selected zero-noise
scores with material-specific costs. In the [427-photo faint comparison](full427-faint-adc.md),
it lowers Corpus20k's weakest-band RMS from 2.594 to 1.901 DN16, effectively
matching projected V120 at 1.900 DN16. Both standing positive-noise GFX sets
bypass the helper exactly. The [588-color review](full-corpus-control20k-color-review.md)
still shows slightly worse Corpus20k worst-case bias and RMS than exact Malvar.

| Component family | What worked | What remains unresolved |
| --- | --- | --- |
| [V187/V195/V198/V200 wave heads](scale-supported-cfa-wave-comparison.md) | V198 EMA reaches 11.158% of constructed-GT mesh amplitude; V200 slightly reduces quiet/flat error at 11.102% response; V187 is quieter and V195 avoids the new building fringes | Incomplete crossings, false texture and green/magenta building fringes. Amplitude response is not overall accuracy |
| [Local support and neural nuisance](neural-nuisance-full-panel.md) | Lower added quiet/increment error than analytic local waves and smaller building bands | Much weak detail remains absent; errors still slightly above the parent |
| [A-only innovation validation](parent-innovation-validation.md) | Weaker false color in the fixed building crop, with analytic correction RMS from V120 down from 30.10 to 17.46 DN16 | Higher ISO1600 weak-increment error on colored wires and soft cab crossings |
| [Scene spectral gain](scene-spectral-detail.md) | Slightly lower longer-band error on 64 positive-noise development sources | Fine weak-band and quiet errors rise. Aligned context has negligible effect, and fine cab crossings remain incomplete |
| [Retuned scene spectral gains](scene-spectral-gain-headroom.md) | Keeping the longer component alone gives a small longer-band gain with near-parent quiet errors | Source-disjoint retuning worsens fine and quiet errors. Even target-assisted gains have little leverage over fine detail |
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
