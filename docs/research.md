# Research directions and literature

Reviewed November 17, 2026. The central problem is recovering measured weak
structure without adding texture to quiet regions. More recovered amplitude
has repeatedly come with extra flat-region error or false color. The
[experiment index](experiments.md) summarizes the completed evidence;
[current model choices](current-model.md) describes available operating points.

## Priorities

1. **Supply whole-photograph context.** Existing V120 DINO features see the local
   tile. A shared spatial scene encoding could distinguish sky from a fence-rich
   region and condition smoothing or refinement. RAW measurements must still
   determine fine phase, orientation, color and amplitude. Test correct versus
   shuffled/masked context and include wires in sky and flat gaps beside fences.
   The [completed64-source study](whole-scene-context-development64.md) finds
   quiet-coarse gains but no established weak-detail benefit from correct spatial
   placement. The [completed camera panels](whole-scene-context-camera-review.md)
   show partial unseen repair versus local-only but regression versus V120.
   Full427 photos are still collecting.
   With local RAW fixed, the [near/distant preview intervention](scene-context-extent.md)
   finds distant influence on the real foliage and coarse fence. Blurring near
   the tile changes the two development sources more, with mixed weak-band errors.
   In the [wire and gap test](scene-wire-gap.md), a stronger aligned distant
   continuation and an orthogonal guide produce almost the same native weak
   response at ISO400 and ISO6400. The [expanded matched run](expanded-scene-corpus.md#matched-12000-update-continuation)
   starts both arms at 100k and uses the same 24,000 distinct context scenes.
   The [explicit RAW line fit](isolated-raw-line.md) instead estimates one
   isolated outer line and checks independent local Bayer samples. It recovers
   about 81% of the partial ISO400 increment with 2.40 DN16 added gap RMS
   on fresh cases. High-noise support and proposals for repeated real mesh
   remain open.
   The [scene-conditioned spectral pilot](scene-spectral-detail.md) routes
   whole-image context to the strength of measured RAW detail. Both trained
   heads improve longer-band error slightly and worsen fine and quiet errors.
   Aligned features and shifted features yield nearly identical predictions.
   The [fixed-proposal gain fits](scene-spectral-gain-headroom.md) find little
   extra weak-detail recovery even with exact local targets. The source-disjoint
   calibration favors higher gains and raises fine and quiet error.
   The [whole-photo patch covariance test](scene-patch-covariance.md)
   conditions the shape of a native green innovation with nearby or
   similar exterior patches. Transposed covariance performs similarly
   on independent natural targets, and calibration under independent
   noise selects zero correction. Two-green confirmation improves response
   at a fixed correction dose, with higher quiet and increment error.
   [Separate donor validation](scene-patch-crossfit.md) lowers flat
   error on coherent repeats and improves planted-wire response at
   matched flat error. The new natural-photo panel has higher
   increment and flat error. The fitted band covers the measured
   fine-cab peaks and starts above the longer planted-mesh fundamental.
   [Wider measurement windows](scene-patch-width.md) improve both real
   peak projections in a clean-signal basis check. The same-band
   32-pixel window lowers short-wire error inside planted gaps at
   nearly equal flat error. Real fine crossings stay incomplete and
   the wire-calibrated strengths raise natural-photo error.
   A disjoint RAW direction guide also improves the ISO400 far-wire result
   in eight reused synthetic geometries, with no clear ISO6400 weak-detail
   benefit. The real cab comparisons show stripe suppression on one side
   and stronger diagonal modulation on the other. [Direction-guide test](scene-wave-guides.md).
   Fitting a phase profile from query RAW improves lower-noise recovery beyond
   a sine wave on a different retained draw across all four CFAs. ISO6400 still
   trades weak response for higher quiet and increment errors. Shrinking the
   fit reduces both costs at the permissive threshold. At equal measured
   quiet error, it has lower false weak projection and lower weak response
   than uniform attenuation. Calibrating pooled scores on seven geometries
   and evaluating on the eighth gives a repeatable lower-noise gain. It
   leaves high-noise weak recovery and real fine crossings open.
   [Phase-profile test](guided-phase-profiles.md) · [Equal-quiet shrinkage](guided-phase-fit-shrinkage.md#iso6400-at-equal-measured-quiet-error) ·
   [Pooled RAW support](fold-support-pooling.md).
   At ISO6400 far, phase agreement has the same positive rate with
   the weak wire present and absent. Attenuating by agreement lowers the
   building correction and reduces weak response at matched quiet error.
   [Phase-agreement test](phase-profile-agreement.md).
   Comparing the original and half frequencies on donor RAW repairs
   both guide misses. The lower-noise far response improves at equal
   quiet error. The high-noise case still has little recoverable response
   at the conservative gate. [Donor subharmonic test](donor-subharmonics.md).
   Two-to-one validation rectangles along and across the wire retain less
   weak response than the square under the tight quiet budget. The
   ISO6400 wire-free edge control gives essentially the same error for
   all three. [Oriented validation](oriented-raw-support.md).
   Pooling actual CFA evidence across colors gives a small near-edge
   ISO400 response gain with higher increment error, and less far-edge
   response at both noise levels under the tight quiet budget.
   [Joint Bayer phase-profile evidence](joint-phase-profile-support.md).
   Selecting waveform harmonics from a disjoint RAW donor keeps more
   response than the fundamental alone. The full phase basis recovers
   more weak signal in every held-out budget cell.
   [Donor waveform comparison](donor-phase-support.md).
   Refitting the delivered phase on all query sites changes little
   with uniform spatial weights. Giving more weight to sites with
   positive pooled support improves ISO400 far response and increment
   error. The gain survives a descriptive matched-quiet check in all
   eight retained geometries. [RAW refit test](phase-refit-delivery.md).
   The gain repeats for all eight fresh ISO400 far geometries with
   accurate guides and settings frozen on development. Absolute quiet
   error exceeds the development budget, and tight ISO6400 shows little
   or worse weak response. [Fresh-geometry refit test](fresh-phase-refit.md).
   Bounded, fold-local frequency search repairs a one-bin radial error
   at ISO400 far. Frequency choices can drift on accurate near-edge
   guides, with higher delivered no-wire correction. ISO6400 radial
   recovery is small. [Guide-error test](phase-guide-recenter.md).
   Excluding an 8-pixel band during the discovery search improves ISO400
   near-edge guide accuracy and response while retaining the far-edge
   repair. Held-out validation still uses its original RAW samples.
   [Edge exclusion](phase-guide-edge-guard.md).
   Fitting one waveform with signed Bayer amplitudes lowers far-edge
   chroma error slightly. Near-edge weak response falls even at
   matched quiet error. [Shared waveform](shared-phase-shape.md).
   A disjoint donor shape retains more ISO400 far response than a
   harmonic-phase scramble at the original settings. At matched quiet
   error the independent fit still recovers more true near-edge detail.
   [Donor waveform](donor-waveform.md).
   Same-side validation improves dark-side ISO400 recovery at matched quiet
   RMS. Bright-side recovery drops, and separately fitting the waveforms
   loses more overall response. [Same-side comparison](phase-edge-side.md).
   On fresh near-edge geometries, admitting cross-edge bright-side evidence
   reduces response at matched quiet error. Replaying with fixed accurate
   donor frequencies improves ISO400 recovery and increment error.
   [Fresh asymmetric test](asymmetric-phase-evidence.md).
   A RAW cross-check on two disjoint discovery subsets helps with already
   accurate donor guides and rejects some useful repairs of shifted guides.
   Fine cab crossings remain incomplete. [Guide cross-check](phase-guide-crosscheck.md).
   Searching the noisy query for curvature worsens ISO400 response and
   leaves both real fences unchanged. Exact curvature helps lower-noise
   far-edge weak response. Test geometry measured in stronger, disjoint
   parts of a scene with query-local amplitude and support. [Phase drift](phase-drift.md).
   A stronger adjacent donor raises lower-noise far curved response
   from 2.60% to 4.29% at matched quiet error. Only one curved source's
   weak direction is accepted under either profile. Both real fences
   fall back to the guarded fit. [Measured donor geometry](donor-phase-geometry.md).
   Opposing donors improve lower-noise far recovery. The individual
   planar checks resolve period-mismatch failures on the stress panel.
   Real donor neighborhoods reveal rails and cab geometry interrupting
   the lattice. Scene context can help choose compatible donor regions
   before comparing their RAW evidence. [Opposing donors](bracket-phase-geometry.md).
   Searching a wider RAW window finds compatible straight-wire donors.
   On the cab, the search selects a shared coarse carrier from different
   surfaces. Test spatial context for same-surface donor selection and
   keep the screening preview independent of query validation.
   [Screened donor search](search-donor-geometry.md).
   Full-frame DINO affinities shift the left cab donors slightly, with
   train geometry still supplying one side. In a synthetic ambiguity
   test, spectral-score weighting selects the intended pair in 9/96
   cases. Ranking spectrally viable pairs by affinity alone identifies
   the intended pair in 75/96. Test the delivered result under independent
   RAW validation. [Whole-frame donor ranking](screened-scene-donors.md).
   The [appearance-first replay](affinity-first-donors.md) improves
   measured recovery on fresh ISO400 fields with distinct paints.
   Same-paint pairs demonstrate the remaining support limitation.
   Widening the second-family search recovers curved donor geometry in
   four retained two-family views. The extra query delivery stays small.
   [Localized validation](localized-donor-validation.md) finds that
   narrower donor windows make rail boundaries easy to mistake for
   repeated structure. Modeling two boundaries reduces false approvals
   while preserving weak response. The fixed-bracket replay leaves
   how often whole-frame context can place both windows on the same
   surface unresolved.
   [Searching both windows](scene-window-donors.md) improves on
   spectral ranking under the ISO400 quiet allowance, with near and
   full-frame context choosing the intended frames equally often.
   Full-frame appearance protects the building. The fixed-bracket
   lead and the cab donor crops point to the remaining selection
   problem. A straight-path appearance score does little to solve it.
   [Query background and score controls](query-rail-background.md)
   find that a two-boundary fit suppresses rail and building artifacts
   with similar weak response. Dropping the amplitude penalty in a
   fixed-shape matched score produces more quiet error and less
   recovery after quiet matching, even with exact center frequencies.
   [Same-color phase pooling](surface-phase-aggregation.md) gives
   a small ISO400 response gain with the original wave gate on two
   geometry sets. [Signed local bounds](local-phase-bounds.md)
   control peak errors while retaining most of that response.
   Local energy control also lowers rail RMS, with weaker wire
   recovery. All fresh complex rails still trigger corrections
   when given misleading guides. Suppressing those admissions
   requires improving the predictive background or evidence.
   [Flexible query boundaries](flexible-query-edges.md) suppress
   many complex-rail artifacts, while straight steps and rails
   regress at the original gate. With exact guides and finite
   wire added beside rails, the faint increment remains mostly
   unrecovered. Preserve the parallel fallback where additional
   shape parameters have little predictive support.
   [Nested screening](screened-query-edges.md) compares curved
   shapes on reserved discovery samples against both hard and
   smooth parallel models. It retains the complex-rail mitigation
   and most straight-edge behavior. The positive archive
   returns to the parallel refit, with the same weak response
   beside rails as the unscreened curves.
   [Cross-color validation](cross-colour-refit.md) changes only the gate
   and recovers little extra near those rails, even with exact frequencies.
   Bounded partner support helps ordinary ISO400 wires slightly and raises
   false rail RMS.
   [Fixed finite envelopes](wire-envelopes.md) and a fundamental-frequency
   fit improve fresh ISO400 response from 0.86% to 13.77% beside complex
   rails, with lower increment error. A correctly centered broader
   footprint retains 12.14% response and reduces complex-rail false
   correction. Displacing it by 40 pixels loses nearly all recovery.
   ISO6400 increment error rises despite greater average response.
   A context-derived footprint needs a reliable location and reserved
   RAW validation for straight rails and high-noise cases.
   [Reserved RAW footprint selection](reserved-wire-footprint.md) estimates
   that location from the stronger direction and tapers only the other.
   At the uniform quiet limit the ISO400 offset response rises from 1.67%
   to 7.58%, with increment RMS falling from 5.90 to 5.77 DN16.
   The simpler two-direction taper raises error. ISO6400 locations are
   unreliable, and the estimate leaves the fine cab crossings unresolved.
   The [whole-image guide replay](scene-wire-footprint.md) retains the
   sinusoid gain and shows regressions on ordinary finite wires. Using all
   eight knots prevents most of the fundamental loss. A companion
   validation check limits the regression but seldom admits a taper.
   The exact-center comparison and the low number of accurate weak
   proposals separate losses from the waveform fit and missed geometry.
   The [wider frequency bank](donor-frequency-bank.md) adds an accurate
   candidate on six of eight main ISO6400 cases, while the reserved
   query chooses none. Selecting the nearest confirmed frequency with
   the known target still recovers less than 1% of the weak amplitude.
   Better candidate coverage alone leaves little leverage under the
   existing query fit and admission policy.
   [Shared perspective](shared-projective-phase.md) improves geometric
   agreement at ISO400 by letting the stronger direction estimate the
   change in spacing of the companion. The gain is small after independent
   RAW admission, and the native cab mesh is still unresolved.
   The [narrow-profile study](finite-wire-profiles.md) finds that an exact
   footprint raises eight-knot representation from 17% to 91% of the
   constructed weak-wire energy. An estimated footprint helps a compact
   width/phase fit on selected ISO400 wires. Conditional localization
   keeps flat and rail corrections small on fresh controls, with mixed
   results across wire geometries.
   The [localized frequency replay](localized-guide-frequency.md) finds
   that the exact weak frequency fails the carrier-absent check in a
   reserve fold on all 24 shifted-guide inputs. Better spatial support
   alone does not make the present waveform evidence discriminative.
   [Implementation](whole-scene-context-next-test.md).
2. **Test longer full-model training with broader data coverage.** Many possible
   crop/noise examples remain unused. Measure held-out learning curves at matched
   data, schedule and compute, including weak detail and flat-region errors.
   Failed small-head trials do not establish a full-model scaling limit.
   The completed [100k full-corpus continuation](full-corpus-long100k.md)
   covers five complete ordinary-photo passes and 78,013 sixth visits.
   It gains 0.575 dB on retained faint ADC fields versus V120 and improves
   fine-band error on three of four materials. The gain over 86k is
   0.006 dB, selected flat-color bias rises, and fine GFX crossings
   remain incomplete. The
   [completed20k control](full-corpus-control20k-review.md)
   actually covers all90,778 photos and recovers most10k faint loss, but remains
   0.02061 dB below V120 with higher fine-band error for3/4 materials. Both fences
   remain incomplete. Coverage, reviewed quota and execution co-vary; they do not
   isolate a cause. [Broader primary/weak-band evidence](full-corpus-primary-admission.md)
   is collecting/queued. The [complete camera panels](full-corpus-control20k-camera-review.md)
   gain0.03285 dB known/lose0.04067 unseen; most added unseen arithmetic MSE is
   channel DC,with spatial error also higher. Track both separately. The
   [calibrated ADC-bin diagnostic](adc-bin-consistency.md)
   improves selected zero-noise errors with material regressions; the full588
   [palette review](full-corpus-control20k-color-review.md) is complete: raw20k
   worst bias765.7 DN16 versus V12055.5,mostly repaired by Malvar/bins; bins gives
   small V120 aggregate gains versus exact Malvar with20k tail tradeoffs. The
   [427-photo faint ADC study](full427-faint-adc.md) finds higher raw Corpus20k
   weak-band error than V120. ADC-bin projection lowers it from 2.594 to 1.901
   DN16, effectively matching projected V120. The long trajectory retains10k
   state,with recorded data/conditioning/RNG matching the control10k prefix
   apart from declared order-header identities. Preserve its original schedule.
   [Coverage and pipeline rationale](training-scale-pipeline-review-2026-11-17.md).
3. **Evaluate the delivered correction.** Better background prediction or a
   stronger synthetic mesh response does not guarantee lower final-image error.
   The [full guided panel](neural-guided-phase-full-panel.md) and
   [colored-wire study](coloured-fine-wire-benchmark.md) expose this gap.
   The [A-only innovation control](parent-innovation-validation.md) reduces
   building fringing at the fixed crop. The native review confirms little
   change in cab crossings and a small increase in signed-color increment error.
4. **Establish a production speed baseline, then optimize against it.** Separate
   decoding, context encoding, trunk, overlap, transfer and output costs. Benchmark
   batch/precision changes on the current model before selecting them. Shared
   scene conditioning is implemented; efficient reconstruction and distillation
   still need testing. No shared-context production speedup is measured.
   [Runtime/context review](weak-detail-global-context-production-review-2026-11-16.md).

## Reading and design notes

| Document | Scope and date |
| --- | --- |
| [Weak-detail literature review](weak-detail-literature-2026-11.md) | Initial November 15 literature search, with explicitly added follow-ups; primary-paper links and proposed tests |
| [Global context and production review](weak-detail-global-context-production-review-2026-11-16.md) | November 16 evidence snapshot, scene-context ideas and runtime plan |
| [Training scale and pipeline review](training-scale-pipeline-review-2026-11-17.md) | November 17 corpus coverage, training budgets, batch size and pipeline proposals |
| [Whole-scene context test](whole-scene-context-next-test.md), [64-source review](whole-scene-context-development64.md), [camera panels](whole-scene-context-camera-review.md) | All3 matched2k arms,64-source/intervention study and both camera panels complete/native-viewed. Small quiet gains/partial unseen repair versus local-only; unseen remains below V120 and fine crossings missing. Full427 photos collecting |
| [Full-corpus scaling](full-corpus-scaling.md), [20k review](full-corpus-control20k-primary.md), [100k review](full-corpus-long100k.md) | Both fixed broad evaluations and native reviews are complete. 100k gives +0.20739 dB on 427 photos and −0.03046 dB on unseen measured CFA versus V120. Fine GFX crossings remain incomplete |

These are research proposals and bounded experiment conclusions. They do not
establish broad state-of-the-art quality. Dates describe the source review;
this cleanup adds no new literature search or model evaluation.

## Earlier evidence and references

The [archived research catalogue](history/before-2026-11-17-cleanup/research.md)
preserves the detailed hypothesis table, foundation-model references, frequency
and wavelet notes, and links to all earlier trials. Its chronological updates
are historical. New experiment results belong in their own report and a concise
row in [experiments](experiments.md), following the
[documentation maintenance guide](documentation-maintenance.md).

<a id="foundation-features-and-the-new-objective"></a>

The earlier [foundation-feature architecture and pinned-encoder notes](history/before-2026-11-17-cleanup/research.md#foundation-features-and-the-new-objective)
are retained in the archive for existing inbound links.
