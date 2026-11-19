# Current model choices

Reviewed November 18, 2026. **V120 Small is the general inference recommendation.**
The [Corpus 100k EMA](full-corpus-long100k.md#broader-evaluation) is the strongest
measured option for the fixed photo benchmark at 37.24747 dB, +0.20739 dB over
V120. It loses 0.03046 dB on the unseen measured-CFA panel and has a visible
clipped-petal failure. The [completed64-source scene review](whole-scene-context-development64.md)
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
The 20k control's [full427 benchmark](full-corpus-control20k-primary.md) is complete. The
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
| [Corpus control20k](full-corpus-control20k-primary.md) | 37.09079 dB on the fixed photo panel, +0.05071 dB versus V120, with 420/427 source means improved. Weakest ADC band error falls 1.79% across its contributing sources | Known/unseen +0.03285/−0.04067 dB. Fine-band error rises on three of four retained materials. Worst ADC mean error 765.7 versus 55.5 DN16 and missing fine crossings in both GFX families. [Native endpoint review](full-corpus-control20k-review.md) |
| [Long schedule at 20k](full-corpus-long20k-native.md) | Fine-band RMS improves for bark, fur, and wood against both V120 and short 20k; faint camera-RGB PSNR is +0.15853 dB over short | Rendered faint PSNR is −0.19124 dB versus short. Grass, flat spot checks, and fine cab crossings remain weak. This checkpoint has a scoped native review |
| [Long schedule at 50k](full-corpus-long50k-native.md) | Retained ordinary and shadow sRGB are +0.020/+0.044 dB over V120 | Faint fine-band RMS rises on all four materials versus V120. Bright orange ADC mean error reaches 1,490 DN16 in a BGGR spot check, with visible unevenness. Fine cab crossings still incomplete |
| [Full-corpus 100k](full-corpus-long100k.md) | 37.24747 dB on the fixed 427-photo panel, +0.20739 dB versus V120 and +0.15668 versus Corpus 20k. Known CFA +0.02436 dB versus V120. [Weakest fine-band response](full-corpus-long100k-weak-band.md) improves from 78.57% to 79.47% at ISO100 | Photo quality option. Unseen CFA −0.03046 dB versus V120. ISO12800 weakest response stays near 36.5%. Clipped highlights, orange bias, fine grass and incomplete fine cab crossings remain weaknesses |
| [Expanded scene local-only 12k](expanded-scene-local12k.md) | +0.093/+0.088 dB over its 100k parent on the two development conditions. Both standing GFX reviews complete | Known/unseen CFA −0.02934/+0.00040 dB versus parent. Thin suspension lines and fine cab crossings remain incomplete. Full427 photos collecting. [Fixed camera comparison](expanded-scene-12000-cameras.md) |
| [Expanded scene spatial 12k](expanded-scene-spatial12k.md) | +0.0165/+0.0044 dB over local-only at the two development conditions. The aligned guide raises ISO400 weak response by 0.081 percentage points versus the neutral scene | Known/unseen CFA −0.04909/−0.00341 dB versus parent. ISO6400 quiet error rises with the aligned guide. Fine GFX crossings remain incomplete. Full427 photos collecting. [Fixed camera comparison](expanded-scene-12000-cameras.md) |
| [Localized contrast 2,400](scene-local-contrast-2400.md#completed-64-photo-comparison) | Four EMAs reviewed on 64 photos and both GFX families. Plain local reduces ISO6400 coupled fine-increment RMS from 102.99 to 102.66 DN16 versus Corpus 100k | Adding aligned scene features raises flat-core variation slightly in both recipes. Corpus 100k retains the lowest flat RMS and higher fine response. Fine cab crossings remain incomplete and fixed broad panels are collecting |
| [Matched near-ADC continuation](near-adc-bridge-training.md) | At the smallest positive prior, 0.027 dB faint-photo gain versus control. Fixed RAW corrections reduce weakest-band error from 2.941 to 2.350 DN16 | Raw reserved magenta bias rises from 28,798 to 34,629 DN16 versus control. The fixed repair reduces it to 141 DN16, above the repaired V120's 75. Fine GFX crossings stay incomplete. Known/unseen CFA +0.00279/−0.00402 dB versus matched control. Full427 collecting. [Fixed camera audit](near-adc-bridge-cameras.md) |

The [calibrated ADC follow-up](full-corpus-long50k-native.md#calibrated-adc-follow-up)
reduces the 50k worst spot-check bias to 11.16 DN16 and improves faint
sRGB. Compared with V120 using the same projection, 50k still has
higher mean fine-band RMS and higher flat bias.

The [64-photo noise follow-up](full-corpus-faint-noise.md) finds 100k
reduces faint ISO6400 weak-band RMS by 0.76 DN16 versus V120,
with almost the same signed detail. Lower variation accounts for
95% of the MSE reduction. The fixed bounded lift helps at tiny
noise across all five checkpoints.

The [86k ADC follow-up](full-corpus-long86k-adc.md) gains 0.518 dB in
rendered PSNR on 64 faint photos, with worse weakest-band RMS in raw
86k. Bin Malvar brings that band to 2.208 DN16 versus projected V120 at
2.269. The full flat-color grid exposes a worst raw bias of 1,429.92 DN16,
which bin Malvar reduces to 12.87. The four-material noise sweep gains
detail at very small positive noise and stays near V120 at the ISO100
and ISO6400 priors.
The [near-ADC follow-up](noisy-cfa-residual.md) finds that an opt-in
bounded residual lowers 86k's weakest-band error from 2.744 to 2.360
DN16 on the prospective subset and reduces the reserved palette's
worst bias from 19,449 to 105 DN16. It applies only up to eight
ADC codes RMS at full signal. The separate
[coarse color correction](coarse-adc-color.md) reduces the worst
intermediate-noise palette bias from 6,703 to 810 DN16.

The broad PSNR means, the four-source faint-detail means, and ADC-only photo means
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

The [paired luminance head](paired-luminance-detail.md) adds 0.47
percentage points of target-aligned ISO6400 fine response on the
64-photo panel above Corpus 100k. Fine-increment RMS drops 1.09 DN16
with coupled noise and rises 0.31 DN16 with independent noise. Two
green support windows reduce excess flat texture against a
strength-matched wider guard. Fine cab crossings remain incomplete.
[Eight-orientation replay](paired-head-symmetry.md) finds little
change in independent-draw error at matched correction strength.
[Three same-law redraws](paired-repeat-stability.md#starting-model-on-64-photos-with-three-redraws)
show the paired head's independent-draw variance increase
offsetting its reduction in shared increment error.
[Completed standard repeat training](paired-repeat-stability.md#final-1200-update-evaluation)
reduces ISO6400 independent error with the stronger weight
while losing 0.58 percentage points of response versus Corpus 100k.
[Bayer innovation smoothing](paired-feedback-paths.md) slightly
reduces error versus a response-matched paired head. The standing
fine mesh and the tradeoff versus Corpus 100k remain.
[Quiet-region smoothing plus the fine lift](paired-flat-companion.md)
reduces exact-flat RMS by 0.164 DN16 with a small positive
fine response. High-noise increment error remains mixed.
[Weak-edge training and a measured-step gate](weak-edge-distill.md)
find smaller near-step errors from local attenuation.
The independent-exposure teacher reduces near-step error versus
the same-draw teacher while increasing whole-core error.
Both variants leave the fine cab crossings incomplete.
[Surrounding RAW strength](context-strength.md) varies across sky and fence,
with negligible fine-reconstruction effects at matched response. Per-block
exact-target scaling also gives little gain with the fixed proposal.
[Native-green innovation smoothing](green-phase-innovation.md)
reduces near-step error and increases whole-core error at similar
response, with fine real crossings still incomplete.
[Native green alias separation](quincunx-green.md) extracts a small
additional aligned component in planted aliases. Exterior RAW reduces
added flat variation, with little weak-detail gain at matched strength.
[Checked Bayer curvature](query-phase-curvature.md) gives a small
gain on planted bent patterns at similar gap projection. Its wider
backup recovers more with larger false gap response. On the standing
cab only small center-frequency changes pass, and fine intersections
remain soft.
[Sensor-anchored Bayer fits](query-frequency-consensus.md) retain the
right-cab correction across nearby crop placements and leave the
standing sky and left crop smooth. The pooled fit recovers roughly
the same weak signal as a single query on fresh exact fields and
still leaves incomplete intersections.
[Reserved Bayer query search](query-bayer-reserve.md) finds two fine
directions automatically on the right cab and preserves the sky and
standing left pair. The right lattice is more visible, with soft and
uneven intersections. Fresh exact-target tests show less gap leakage
and a small average loss of weak response versus exterior selection.
[Narrow peaks in exterior RAW](donor-peak-prominence.md) find planted
frequencies more often and retain a weak-detail gain with a joint
calibration limit on flat texture and gap changes. Both standing GFX
families were viewed. The fine cab crossings remain incomplete.
[Local support with exterior phase](green-gap-validation.md) recovers more
of a planted weak carrier than a local free-phase fit while cutting
added flat variation. Coherent gap leakage rises. The automatic GFX
frequency search misses the fine mesh. Supplying prior noisy-RAW peaks
makes more of the right cab lattice visible, with irregular coverage and
overly regular spacing in places.
[Full-epoch scene training at update 2,000](scene-full-epoch.md#first-matched-quality-comparison-at-2000-updates)
finds lower coupled flat-core variation with the matched preview
versus masking, with higher fine-increment error. The first standing
review finds incomplete fine cab crossings in both arms.
[Projected repeat training](paired-shape-stability.md#final-performance-on-the-96-photo-panel)
recovers some of the response lost by standard repeat training,
with higher independent-draw error than the ordinary control
at matched response. Both standing GFX scenes remain soft in
the finest structures.

The [isolated RAW line fit](isolated-raw-line.md) recovers about 81%
of the weak increment through interrupted synthetic ISO400 wires.
Its short support check lowers added gap RMS from 8.70 to 2.40 DN16
versus 64-pixel fits. It still attenuates some true wire ends and
returns the local parent on both standing GFX families.

The [multi-line RAW pilot](multiple-raw-line-guides.md) extends that fit to
competing exterior ridges. It recovers much more of the ISO400 continuous wire
and some of the interrupted wire. Confirming both RAW shoulders of each
ridge removes the measured false correction beside a step on the fresh
panel. Most ISO6400 query output stays near the parent even with accurate
exterior geometry. Both GFX scenes still have missing fine detail.

[Longer local pooling](weak-line-pooled-evidence.md) raises the ISO6400
continuous parallel-wire response from 6.3% to 36.6% with noisy exterior
guides. Interrupted wires still have limited evidence at ISO6400, and
ISO400 gap selection trades lower wire error for some false extension.
The [joint crossing fit](joint-mesh-phase.md) reduces that separate
additive model's ISO400 junction error with known geometry. It can
still extend periodic support across missing sections. Both GFX scenes
return their local parents because the exterior phase checks reject
the tested pairs.

The [local donor mesh trial](local-donor-mesh.md) admits two directions
in the left fine cab crop under both priors. Their predictions improve
held-out RAW error, and the native fit shows a faint lattice. The right
crop and non-fence controls return their parents after the extra check.
ISO6400 recovery on the retained synthetic panel stays weak.

The [overlapping, sensor-anchored mesh fit](local-mesh-stability.md) keeps
the left-cab lattice across crop shifts and returns the five control
views to their parent. The correction also transfers to V120 and Corpus
100k on the same camera observations. On a fresh ISO400 occluded-wire panel it
recovers 76.32% of the target weak contrast against 31.02% for the trunk.
Every synthetic ISO6400 case keeps the parent. The opt-in crop API still
has limited support for broken or changing wire geometry.

The [donor-perspective trial](local-mesh-projective.md) uses shorter
query support to reduce added texture inside known ISO400 mesh gaps
from 3.34 to 0.16 DN16 RMS at near-equal weak response. It also reduces
response on the continuous synthetic mesh and fades the real cab lattice.
The [crossed gap option](local-mesh-gap-support.md) preserves all eight
archived GFX outputs and reduces spill in two of six fresh ISO400 round
gaps. It misses the six rotated strip gaps. Enable it with
`suppress_gaps=True` in the experimental planar crop helper.
The [distributed Bayer audit](local-mesh-distributed-audit.md) reduces
added strip-gap texture from 9.76 to 5.42 DN16 RMS in a fresh ISO400
panel. It weakens one continuous wire beside an intensity step, and
both GFX scenes reproduce the column audit exactly. The distributed
assignment remains a research variant.

The [adjacent donor fallback](donor-phase-transport.md) uses a nearby
tile to propose both directions missed by the usual donor search. The
right cab shows new crossings under both priors with positive local
RAW prediction gains. Some crossings are soft and the lattice is more
regular than parts of the ISO100 reference. Use `adjacent_donors=True`
in the experimental crop helper. The exterior phase fit helps
continuous synthetic ISO6400 wires and can extend texture into gaps.

The [smooth RAW support study](smooth-mesh-support.md) localizes some
ISO400 gaps and fades continuous wires alongside steps. A retrospective
fit with a shared step restores the continuous cases and lowers added
gap texture. The largest ISO6400 gap persists even with known support
and phase in the audit. The new masks remain research variants.

The [contrast-step study](mesh-step-continuity.md) tests true gaps and
continuous wires that change contrast across an edge. Fitting both
wire amplitudes on each side changes one of six continuous ISO400
outputs, compared with five for the earlier step mask. The new mask
preserves all four cab crops and misses the largest high-noise gap.
Direct rear attenuation improves wire error on the studied ISO400
cases and both independent ISO400 repeats.

The [refined foreground-edge check](mesh-refined-edge.md) reduces a
false-wire error component in two fresh ISO400 controls. It slightly
raises their total RGB error, misses the ISO6400 gaps and fades a real
ISO6400 rear wire. All eight standing GFX crops reproduce the packaged
adjacent-donor outputs. The refined check remains experimental.

The [finite footprint check](mesh-shrunk-footprint.md) lowers added
texture in all six fresh ISO400 synthetic gaps and leaves the twelve
continuous two-wire outputs alone. It helps one ISO6400 gap slightly.
The nominal left cab lattice fades locally. Both right views keep the
recovered crossings. Finite support remains experimental.

The [pooled gap audit](mesh-pooled-gap-evidence.md) finds enough RAW
evidence to detect six earlier synthetic ISO6400 gaps when the hypotheses
are fully specified. A larger elliptical search reduces spill in one
prior case. On fresh gaps it trails the earlier finite-support check
and slightly softens both right GFX cab views.

[Averaged gap proposals](mesh-averaged-gap.md) raise conditional
high-noise admissions from 21/32 to 27/32 and improve placement at
matched correction strength. They leave more gap error at the fixed
ISO6400 strength. Refitting strength reduces that error with more
attenuation outside the gap. The nominal right cab keeps its crossings.

The [tapered strength refit](mesh-tapered-strength.md) reduces
attenuation outside the true gap on independent high-noise draws,
with a small increase in residual rear signal. Separate strengths
give a small improvement on fresh ISO6400 gaps. Both retain the
nominal right cab while the fitted gap angle can still drift.

[Refining the nominated geometry](mesh-refined-footprint.md) reduces
ISO400 gap error and exterior attenuation at matched strength. It
adds no fresh ISO6400 admissions and cuts some genuinely continuous
wires at ISO400. Fine cab crossings remain soft.

A [curved foreground and smoothly varying rear model](mesh-gap-information.md)
prevents six false cuts on continuous ISO400 wires and preserves
the control’s gap outputs when used only in the audit. Joint
nomination and audit increase error in the independent ISO6400 repeats.

[Soft sharing of signed color from nearby RAW](mesh-donor-tint.md)
adds two conditional ISO6400 admissions over the curved-affine
local audit, with more exterior attenuation. All fresh matched
crops and the standing GFX crops retain the local-audit pixels.

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

[Cross-color RAW validation](cross-colour-refit.md) gives small ISO400
gains on ordinary wires when another color corroborates the direction.
The bounded gate increases complex-rail false correction, recovers
essentially the same faint signal beside rails and leaves the fine cab
mesh at V120. The screened per-color gate remains the experimental baseline.

[Finite wire support](wire-envelopes.md) with a known ellipse and a
fundamental fit improves ISO400 synthetic weak and strong response beside
rails. A centered broader footprint retains most of the gain, while
misregistration loses it. ISO6400 increment error rises. On GFX, the
uniform fundamental fit produces a smaller spectral building correction
and preserves the coarse lattice. The fine cab crops stay at V120.

[Reserved RAW footprint selection](reserved-wire-footprint.md) gives
better ISO400 weak response and lower increment error when the stronger
direction locates a footprint for the other. Confining both directions
raises increment error. Partner-only false rail RMS is close to uniform,
and the confirmed real crop variants recover no new fine crossings.
The ISO6400 offset panel has essentially no weak response.

[Whole-image footprint replay](scene-wire-footprint.md) finds that
the sinusoid gains do not carry over to finite narrow wires. The
eight-knot basis preserves more weak response than the fundamental,
and the untapered fit has lower ISO400 increment error. Requiring
the partner's own reserve gains largely restores the uniform result,
with one admitted two-direction capture per ISO400 panel.

[Wider donor frequency banks](donor-frequency-bank.md) increase
candidate coverage on the main ISO6400 panel. Independent query
reservation rejects those replacements, and picking the closest
donor-confirmed frequency using the synthetic target raises
weak response only from 0.66% to 0.92%. Donor-only replacement
loses ISO400 detail on both panels.

[Shared perspective](shared-projective-phase.md) raises weak response from
0.38% to 1.15% on constructed ISO400 wires on one plane when only the
companion uses the estimated curvature. Applying the curvature to both
directions raises increment error. The ISO6400 cases gain no recovery and
the fine cab crops still match V120 exactly.

[Narrow wire profiles](finite-wire-profiles.md) recover more of the companion
on two constructed ISO400 wires when confined to a measured footprint. On
the common-plane group, recovery rises from 1.15% to 6.86% with lower
increment RMS. The same rule erases the improvement from footprint-only
fitting on two planar cases. The real fine cab mesh remains unresolved.

[Localized frequency search](localized-guide-frequency.md) cannot recover
the exact weak frequency from a one-bin shift on the measured reserve.
On the main real crop, a spectral fallback strengthens a building
correction without visible new detail. Both cab ROIs stay at V120.

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
