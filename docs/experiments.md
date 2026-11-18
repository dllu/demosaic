# Experiment status and workflow

Reviewed November 18, 2026. This page tracks research outcomes and the next
questions. Use the [model guide](current-model.md) to choose an implementation;
individual reports retain exact measurements, native comparisons and receipts.

## Active and unresolved work

| Work | Evidence available | Next unresolved question |
| --- | --- | --- |
| [Whole-scene context](whole-scene-context-camera-review.md) | All3 matched2k arms,64-source/intervention study, both camera panels and33 final native boards complete, including both GFX families. Spatial unseen +0.01739 dB vs local-only, still−0.05477 vs V120; no convincing new fine crossings | Full427 photos running on CPU with exact canonical inputs and matched CPU V120 |
| [Expanded scene corpus](expanded-scene-corpus.md#matched-12000-update-continuation) | Matched local and spatial preflights pass from 100k EMA on identical noisy scenes. Local-only production arm is training. Each fixed schedule has 24,000 distinct scene visits | Both trained endpoint reviews are pending. The [wire/gap test](scene-wire-gap.md) finds little alignment-specific response from the earlier spatial 2k endpoint |
| [Near-ADC training coverage](near-adc-bridge-training.md) | Completed native and positive-noise reviews from 100k EMA. Small-positive faint photos gain 0.027 dB, with much worse reserved magenta bias. Fixed RAW corrections largely repair that bias and recover more fine detail than the learned change alone | Canonical benchmarks are queued. Fine cab crossings stay incomplete. Corrected V120 retains lower reserved bias |
| [Full-corpus scaling](full-corpus-scaling.md), [short 20k](full-corpus-control20k-primary.md), [long 100k](full-corpus-long100k.md) | 20k completes all three panels, with full427 +0.05071 dB and unseen CFA −0.04067 dB versus V120. 100k uses 1.6M target slots and visits all 90,778 photos five or six times. It gains 0.575 dB on the four faint ADC materials and retains mixed camera scores. Both GFX reviews complete | 20k pixel audit and broad weak-band analysis running. 100k full427 photos collecting. Selected ADC color and missing fine mesh crossings remain concerns |
| [Disjoint RAW direction guides](scene-wave-guides.md) | Matching guide improves lower-noise far weak response from 2.75% to 4.18% and lowers increment error on all eight geometries. Both GFX families viewed | ISO6400 weak response stays near the parent. Cab correction trades some right-side stripe suppression for stronger left-side modulation. Fine crossings remain unresolved |
| [Guided RAW phase profiles](guided-phase-profiles.md), [fit shrinkage](guided-phase-fit-shrinkage.md) | ISO400 far weak response 4.23% to 14.33% versus sine at threshold 2. ISO6400 far shrinkage at threshold 0 reduces quiet RMS from 8.349 to 7.640 DN16 while weak response drops from 11.58% to 5.96%. Both GFX families viewed | Conservative thresholds preserve quiet regions and deliver little high-noise weak response. Cab crossings remain unresolved |
| [Pooled RAW support](fold-support-pooling.md) | ISO400 far weak response 14.19% to 16.89% across held-out geometries at nearly equal mean quiet error. Increment RMS falls from 10.0391 to 10.0222 DN16. Both GFX families viewed | ISO6400 still shows a response/error tradeoff. The small building correction returns and fine cab crossings remain unresolved |
| [Phase-profile agreement](phase-profile-agreement.md) | Building correction falls from 0.421 to 0.166 DN16 RMS. Sky stays identical and coarse fence crossings remain visible | ISO400 far weak response falls to 15.60% at nearly equal quiet error. ISO6400 far agreement is equally often positive with the weak wire present or absent. Cab crossings remain incomplete |
| [Donor subharmonics](donor-subharmonics.md) | Corrects both doubled frequencies in 16 retained donors. Affected ISO400 far response rises from 3.42% to 9.10% at threshold 2, with nearly the same quiet error | Correct geometry barely changes the tight ISO6400 setting. Cab crops reproduce the previous pooled result |
| [Oriented RAW support](oriented-raw-support.md) | The tight-budget ISO400 far square gives 17.54% weak response, compared with 5.40% along and 7.00% across. Both GFX families viewed | Two-to-one rectangles lose response at the tight budget. High-noise far increment RMS improves slightly at lower response. Cab crossings remain incomplete |
| [Joint Bayer phase-profile evidence](joint-phase-profile-support.md) | At the tight quiet budget, weak response drops from 17.54% to 16.52% at ISO400 far and from 2.29% to 2.11% at ISO6400 far. ISO400 near response improves slightly with higher increment error | Independent scoring remains the baseline. Sky matches V120 and the cab crossings remain incomplete |
| [Donor-selected waveform harmonics](donor-phase-support.md) | At the tight quiet budget, ISO400 far weak response is 17.54% full, 16.91% donor-selected, and 7.45% fundamental-only. Sky and both fences viewed | The full basis has higher weak response in all 12 held-out cells. Donor selection slightly lowers tight-budget ISO6400 increment error. The fine cab crossings remain unresolved |
| [Post-validation RAW refits](phase-refit-delivery.md) | ISO400 far response improves from 17.54% to 21.07% with lower increment error and slightly higher quiet RMS. At exactly matched measured quiet RMS, all eight geometries retain an improvement | Uniform refit changes little. Weighted refitting is a useful lower-noise option on the retained panel. ISO6400 and both standing GFX families show the remaining limits |
| [Fresh-geometry weighted refit test](fresh-phase-refit.md) | Frozen settings raise ISO400 far weak response from 20.94% to 23.66% with lower increment RMS on all eight new geometries | Both fits add about 0.039 DN16 against the 0.02 development quiet budget. Tight ISO6400 shows little or worse response. All donors have accurate guides |
| [Bounded phase-guide recentering](phase-guide-recenter.md) | After a one-bin radial error, ISO400 far weak response recovers from 1.36% to 22.33% with quiet error near that of the nominal guide | The search hurts accurate ISO400 near guides, offers little ISO6400 radial repair, and leaves the fine real cab crossings unresolved |
| [Edge exclusions during the guide search](phase-guide-edge-guard.md) | The 8-pixel guard raises ISO400 near weak response from 6.47% to 12.16% with accurate guides and from 6.59% to 10.66% after a one-bin radial error. Far results reproduce the earlier repair | Higher quiet RMS in the lower-noise near comparisons, little ISO6400 recovery, and fine real cab crossings still unresolved |
| [Production speed](weak-detail-global-context-production-review-2026-11-16.md) | Runtime bottlenecks and proposed optimization sequence | Repeatable end-to-end baseline, then measured quality-preserving speedups; 100MP in 10 seconds remains unmet |

## Completed comparisons that guide the next work

The [isolated RAW line study](isolated-raw-line.md) raises partial
ISO400 weak response from 11.12% to 80.58% on fresh examples.
Shorter support lowers added gap RMS to 2.40 DN16. ISO6400 gains
are sparse and both standing photographs return their local parents.

| Question | Finding | Evidence |
| --- | --- | --- |
| Can competing exterior lines support weak local reconstruction? | Matching guides recover 100.53% of the continuous and 35.24% of the interrupted ISO400 crossing increments. A RAW shoulder check removes the false correction beside a step on the fresh panel. Accurate exterior geometry yields little local delivery at ISO6400. Both GFX families viewed | [Multi-line RAW pilots](multiple-raw-line-guides.md) |
| How did the full-model continuation perform? | V131 improves broad photo PSNR by 0.04000 dB, with unseen-camera and severe ADC-color costs. Fixed ADC projection repairs color with a weak-band tradeoff | [Broad V131](v131-broad-primary.md), [ADC option](v131-adc-projection.md) |
| Does local RAW attention help at the full budget? | V132 at 20k loses 0.40978 dB faint ADC versus V131; ordinary detail is tied. The early 1k advantage did not persist | [Matched training](raw-spatial-continuation.md), [V132 endpoint](v132-endpoint-quality.md) |
| Do shared edges or better carrier allocation solve weak detail? | Shared-edge training is quieter but weakens response. Competing orientations help some weak sectors and hurt strong ones. Complementary proposals give a small lower-noise gain | [Shared-edge](shared-edge-comparison.md), [competing](competing-edge-response.md), [complementary](complementary-edge-response.md) |
| Does local support reduce false texture? | It lowers errors relative to global support; neural background prediction further reduces added error. Weak detail and small costs versus the parent remain | [Local full panel](local-wave-full-panel.md), [neural full panel](neural-nuisance-full-panel.md) |
| Does more local context or richer amplitude fitting suffice? | Larger background context loses weak response; local amplitudes increase response with severe building bands. Global background reduces those artifacts | [512-context ablation](neural-nuisance-context512.md), [local amplitudes](spatial-carrier-amplitudes.md), [global-background full panel](global-background-full-panel.md) |
| Does guided phase pooling generalize? | Weak response and full RGB error improve, but quiet/increment error worsens on the full eight-source panel; the pilot increment gain does not persist | [Full guided comparison](neural-guided-phase-full-panel.md) |
| Can extra fine frequencies restore the green fence faithfully? | Fine proposals make both directions more visible. Joint color support reduces tint; fresh signed-color wires still have no useful weak-response gain | [Fine proposal pilot](fine-frequency-proposals.md), [joint color](joint-fine-colour-support.md), [colored-wire validation](coloured-fine-wire-benchmark.md) |
| Can CFA colors share a waveform while estimating signed amplitudes? | Lower far-edge chroma error with smaller weak response. At matched quiet RMS, ISO400 near recovers 7.65% with the shared fit versus 12.00% with independent profiles. Fine real crossings remain incomplete | [Shared waveform test](shared-phase-shape.md) |
| Can a disjoint RAW patch supply a waveform? | At matched quiet RMS, donor shape slightly lowers far-edge increment error and reduces ISO400 near response from 12.16% to 7.54%. Sky matches V120 and the cab lattice stays incomplete | [Donor waveform test](donor-waveform.md) |
| Does held-out evidence need to cross a strong edge? | At matched quiet RMS, same-side evidence raises ISO400 dark-side response from 8.19% to 11.84% while bright-side response falls. Separate profiles lose more overall response. Both real fences reproduce the guarded fit | [Edge-side comparison](phase-edge-side.md) |
| Does the bright side benefit from cross-edge evidence? | The eight fresh ISO400 near scenes favor same-side validation for response at matched quiet RMS. Fixing accurate donor guides raises response from 3.94% to 6.12% with lower increment error. The real fences retain the earlier fit | [Fresh asymmetric validation](asymmetric-phase-evidence.md) |
| Can disjoint RAW samples verify guide moves? | At matched quiet RMS, ISO400 recovery rises from 3.94% to 4.35% near the edge with nominal guides and falls from 22.33% to 19.92% far from the edge with shifted guides. Cab crossings remain incomplete | [RAW guide cross-check](phase-guide-crosscheck.md) |
| Can query RAW estimate changing wire spacing and curvature? | At matched quiet RMS, ISO400 far weak response falls from 8.81% to 6.10%. Supplying exact geometry improves a smaller lower-noise far-edge panel. Both real fences match the planar fit | [Phase drift](phase-drift.md) |
| Can stronger neighboring RAW estimate the phase field? | ISO400 far curved weak response rises from 2.60% to 4.29% against the fixed planar fit at equal quiet RMS. The aggregate response is essentially flat. Both real fences fall back to the guarded fit | [Measured donor geometry](donor-phase-geometry.md) |
| Do donors on opposite sides improve geometry and recovery? | At matched quiet RMS, ISO400 far weak response rises from 9.38% to 12.13% against the fixed planar fit. Individual-planar checks reject all four mismatched donors. One real cab crop changes slightly, with incomplete fine crossings | [Opposing RAW donors](bracket-phase-geometry.md) |
| Does searching surrounding RAW find better donor guides? | At matched quiet RMS, ISO400 far straight-wire recovery rises from 26.42% to 32.48% and curved-wire recovery drops from 10.70% to 1.46% versus fixed donors. Sky is exact and added cab banding declines. Both GFX families viewed, with fine crossings still missing | [Screened donor search](search-donor-geometry.md) |
| Does whole-frame context pick better donors? | Near and full-frame weighting choose the intended pair in 9/96 synthetic cases, versus 0/96 with spectral ranking. Their outputs are identical on that panel. On both GFX families, sky and coarse crossings are retained and fine cab crossings stay incomplete | [Full-frame donor ranking](screened-scene-donors.md) |
| Does ranking by appearance first improve reconstruction? | Intended pairs rise to 75/96 on the retained panel. On fresh distinct-paint ISO400 fields, both context arms give 5.07% weak response versus V143 at 1.60% under the same quiet limit. Same-paint gain is negligible. Curved donor matching gives a small ISO6400 subset gain. Both GFX scenes viewed, with cab crossings still incomplete | [Appearance-first ranking](affinity-first-donors.md) |
| Can a localized donor check distinguish wire from rails? | A two-boundary fit cuts rail-only approvals from 23/24 to 2/24 and preserves 8.71% ISO400 weak response from refined single-edge validation. Native cab fallback removes diagonal banding, with fine crossings still missing | [Localized donor validation](localized-donor-validation.md) |
| Can whole-frame appearance choose two local donor windows? | Near and full-frame ranking choose intended frames on 6/8 ISO400 inputs versus 0/8 with spectra alone. Full-frame preserves the building and rejects 12/12 new rail-only controls. It recovers less than 1% faint response at the parent's quiet level and leaves the cab crossings incomplete | [Scene window ranking](scene-window-donors.md) |
| Can the query distinguish an assigned wire guide from a rail? | Two boundaries lower forced-guide rail error from 7.29 to 0.79 DN16 and suppress false building color with the same spectral guide. ISO400 weak response stays at 4.80% under the full-frame guide quiet cap. Orthogonal matched scores lose response after quiet matching | [Query rail background](query-rail-background.md) |
| Can phase-aligned measurements improve delivery behind the same wave gate? | Capped tangent averaging raises ISO400 weak response from 4.80% to 5.03% and from 6.44% to 6.98% on separate geometries, with lower quiet RMS. Rail RMS is similar, with larger peak errors. Both GFX families viewed, with no new cab crossings | [Surface-constrained phase averaging](surface-phase-aggregation.md) |
| Can local bounds retain faint response and suppress rail peaks? | Signed peaks retain 4.97% and 6.97% ISO400 response on the two geometry sets and remove the previous high rail peaks. Local energy lowers fresh rail RMS from 5.16 to 4.52 DN16 versus refit, with weaker wire response. Both GFX families viewed | [Local phase bounds](local-phase-bounds.md) |
| Does fitting curved rail boundaries improve the predictive null? | Up to four boundaries cut complex-rail RMS from 5.16 to 0.97 DN16 and activations from 24/24 to 17/24. Straight controls regress, and recovery beside a simulated rail stays below 0.4%. Both GFX families viewed | [Flexible query boundaries](flexible-query-edges.md) |
| Can reserved RAW keep curves for the rails that need them? | Screening keeps the complex-rail reduction on new controls, 5.61 to 1.31 DN16, and lowers straight RMS from 0.907 to 0.447 versus unscreened curves. The archived positive predictions match the parallel refit exactly. Both GFX families viewed | [Nested background screening](screened-query-edges.md) |
| Can other CFA colors validate the faint wire? | Bounded partner evidence raises quiet-capped ISO400 ordinary-wire response from 4.80% to 4.97% and from 6.44% to 6.77% on separate geometries. Wire recovery beside rails stays negligible. Complex null RMS rises from 1.31 to 1.52 DN16. Both GFX families viewed and the independent gate stays the baseline | [Cross-color validation](cross-colour-refit.md) |
| Can a finite wire footprint improve recovery beside rails? | Fresh ISO400 response rises from 0.86% to 13.77% with an exact footprint and 12.14% with a wider centered one. Exact increment RMS falls from 6.72 to 5.91 DN16. ISO6400 increment RMS rises. Both GFX families viewed with a uniform fundamental basis and no new cab crossings | [Finite wire support](wire-envelopes.md) |
| Can a stronger wire locate the weaker direction's footprint? | At the uniform quiet limit, reserved-RAW partner support raises ISO400 response from 2.33% to 8.95% and from 1.67% to 7.58% on the independent offset panel, with lower increment error. Rail-only RMS is close to uniform. ISO6400 gains fail to repeat and the fine cab crossings stay incomplete | [Reserved RAW footprint](reserved-wire-footprint.md) |
| Does the footprint transfer to whole-image frequency proposals? | Uniform eight knots give 4.80% and 6.44% ISO400 response on the two ordinary-wire sets. Eight-knot tapering raises increment error on both. The companion check returns both panels near uniform and rejects all 48 forced-guide tapers. Both standing GFX sets viewed with no new cab crossings | [Whole-image footprint replay](scene-wire-footprint.md) |
| Does a wider donor shortlist retain the weak orientation? | Main ISO6400 donor-confirmed coverage rises from 0/8 to 6/8, with no replacements admitted by query reserve checks. Knowing which bank entry to use raises weak response from 0.66% to 0.92%. Both GFX families viewed with no new crossings | [Donor frequency bank](donor-frequency-bank.md) |
| Can the stronger direction supply perspective for a fainter wire? | On six constructed common-plane ISO400 cases, companion-only transfer raises recovery from 0.38% to 1.15% with slightly lower increment RMS. The corresponding ISO6400 estimate never passes the reserve check. Both GFX sets viewed and fine cab crossings remain incomplete | [Shared perspective](shared-projective-phase.md) |
| Can a measured footprint make a narrower wire fit reliable? | A footprint from the stronger wire raises common-plane ISO400 recovery from 1.15% to 1.90% with eight knots and to 6.86% with a narrow companion and conditional reserve margin. The gain concentrates in two cases. Fresh forced-guide rails stay near baseline and fine cab crossings remain incomplete | [Narrow wire profiles](finite-wire-profiles.md) |
| Can anchor support help select the weak frequency? | A localized reserve search rejects the exact frequency in all 24 one-bin shift cases. Whole-image guide accuracy is unchanged on both archived panels. Both GFX families viewed and fine cab crossings remain incomplete | [Localized frequency search](localized-guide-frequency.md) |
| Does physical ADC correction repair the 50k color failure? | Worst selected flat bias falls from 1,490 to 11.16 DN16 with ADC bins. Corrected 50k scores higher on faint sRGB than corrected V120 and has slightly higher fine-band RMS | [50k ADC follow-up](full-corpus-long50k-native.md#calibrated-adc-follow-up) |
| Does ADC projection preserve faint detail across photos? | Across 427 held-out photos, Corpus20k's weakest-band RMS falls from 2.594 to 1.901 DN16, effectively matching projected V120. Both standing positive-noise GFX sets bypass the projection exactly | [427-photo faint ADC study](full427-faint-adc.md) |
| Does the larger-run ADC gain hold across faint photos and noise? | Raw 86k gains 0.518 dB on 64 faint photos with higher weakest-band error and reaches 1,429.92 DN16 worst bias on the full flat-color grid. Bin Malvar lowers those errors to 2.208 and 12.87 DN16. The fine-band gain at tiny positive noise fades at the ISO100 and ISO6400 priors | [86k ADC and noise follow-up](full-corpus-long86k-adc.md) |
| What happens just above the ADC limit? | The bounded residual lowers 86k weakest-band RMS from 2.744 to 2.360 DN16 on the prospective 12-photo comparison and worst reserved flat bias from 19,449 to 105 DN16. Higher priors need the guard. Both GFX families bypass the opt-in helper exactly | [Near-ADC residual and conditioning](noisy-cfa-residual.md) |
| Can coarse RAW consistency repair the next noise level? | Worst reserved flat bias falls from 6,703 to 810 DN16. The held-out photo and standing GFX predictions return exactly | [Coarse intermediate-noise color](coarse-adc-color.md) |
| Does held-out validation of the proposed fine correction improve delivery? | The analytic building fringe weakens at the fixed crop. Cab crossings stay soft and signed-color weak response is essentially unchanged | [A-only innovation review](parent-innovation-validation.md) |
| Does the spatial model use context beyond the tile? | With local RAW fixed, blurring distant preview regions changes foliage and coarse-fence output by 4.14 and 5.15 DN16 RMS. Thin cords and fine cab crossings remain incomplete | [Near and distant preview intervention](scene-context-extent.md) |
| Can scene context guide the gain on measured RAW detail? | Both 800-update heads lower longer-band error slightly. Finer and quiet-region error rise. Shifting spatial features barely changes the delivered result, and both GFX families look close to V120 | [Scene spectral pilot](scene-spectral-detail.md) |
| Can better gains recover the fine detail missing from that proposal? | With fixed support, exact local targets yield only 1.1% lower ISO12800 fine error with unbounded nonnegative gains. Source-disjoint calibration raises fine and quiet error. Both GFX families viewed | [Scene spectral gain headroom](scene-spectral-gain-headroom.md) |

V131 also changes the training cohort, so its gain is not an isolated test of
training duration. The 100k run completed five full ordinary-photo passes and
78,013 sixth visits. Its checkpoints use a100k schedule, distinct from the annealed20k
control whose completed20k review recovers most of the earlier faint loss but
still has mixed fine-detail/color costs.
[Budget, source/crop/noise coverage and runtime evidence](full-corpus-scaling.md).

The synthetic panels differ in parents, sources, noise and metrics. Response
percentages from different rows are not a leaderboard. Both protected GFX scenes
remain required qualitative checks; their separate ISO100 references are not GT.
[Research rationale and literature](research.md).

## Running an experiment

Training recipes bind existing inputs and evidence by checksum. They are local
artifact recipes; the referenced caches/operator/checkpoints must be present.
Do not silently substitute missing sources or refresh their hashes.

```bash
source scripts/env.sh
uv sync --extra dev --extra nonlocal
uv run demosaic-experiment prepare configs/experiments/shared-edge.json \
  .cache/experiments/shared-edge
uv run demosaic-experiment inspect .cache/experiments/shared-edge
uv run demosaic-experiment audit-cache .cache/experiments/shared-edge
uv run demosaic-experiment train .cache/experiments/shared-edge --stop-after 8
uv run demosaic-experiment train .cache/experiments/shared-edge --resume
```

Use a fresh output directory for a new experiment. Preparation snapshots the
package and binds all inputs. Training uses that snapshot. Each committed row
includes head weights, Adam, EMA, RNG and frozen-state identity; resumption skips
the completed prefix. `launch` starts a detached worker with the same options.
[Configuration, export, evaluation and native-crop interfaces](architecture.md).

Reusable recipes include [V200 replay](../configs/experiments/v200-replay.json),
[shared-edge](../configs/experiments/shared-edge.json),
[competing orientations](../configs/experiments/orientation-balanced.json) and
[complementary proposals](../configs/experiments/complementary.json).
Their original completed runs and a fresh invocation of a recipe are separate
experiments; preparation alone does not launch training.

Quality review needs numerical checks and actual native viewing, including
present/absent detail, quiet/flat controls, natural photos and both GFX families.
A completed numerical producer is not a completed qualitative review.
[Evaluation protocol](evaluation.md).

## Historical experiment catalogue

The [pre-cleanup index](history/before-2026-11-17-cleanup/experiments.md),
[detailed research record](history/before-2026-11-17-cleanup/research.md),
[V200-era index](history/experiments-through-v200.md) and
[timestamped diary](../diary/index.md) preserve the longer sequence of trials.
Their running/queued statements describe their writing dates, not current jobs.
