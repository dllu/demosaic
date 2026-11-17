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
   [Implementation](whole-scene-context-next-test.md).
2. **Test longer full-model training with broader data coverage.** Many possible
   crop/noise examples remain unused. Measure held-out learning curves at matched
   data, schedule and compute, including weak detail and flat-region errors.
   Failed small-head trials do not establish a full-model scaling limit.
   The [100k full-corpus continuation](full-corpus-scaling.md#long-schedule-20k-milestone)
   has completed the [matched 20k image review](full-corpus-long20k-native.md),
   with lower fine-band error in three faint materials, worse flat spot checks,
   and lower mean faint sRGB PSNR versus the shorter schedule. The
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
   small V120 aggregate gains versus exact Malvar with20k tail tradeoffs. A new
   427-photo faint study uses original-source masks
   and1708 image/CFA observations/model. Its16 legacy inputs reproduce exactly
   and all427 IDs are val/disjoint currenttrain. The long trajectory retains10k
   state,with recorded data/conditioning/RNG matching the control10k prefix
   apart from declared order-header identities. Preserve its original schedule.
   [Coverage and pipeline rationale](training-scale-pipeline-review-2026-11-17.md).
3. **Evaluate the delivered correction.** Better background prediction or a
   stronger synthetic mesh response does not guarantee lower final-image error.
   The [full guided panel](neural-guided-phase-full-panel.md) and
   [colored-wire study](coloured-fine-wire-benchmark.md) expose this gap.
   The [A-only innovation control](parent-innovation-validation.md) has completed
   numerical review; its published native review is still pending.
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
| [Full-corpus scaling](full-corpus-scaling.md), [20k review](full-corpus-control20k-review.md) | Control complete/all90,778 photos visited; most midpoint faint loss repaired, small ordinary/shadow gains but mixed spatial/color costs. Both fences viewed. [Camera panels](full-corpus-control20k-camera-review.md) known +0.03285/unseen−0.04067 dB. Original100k trajectory/full primary photos and expanded427-source faint study running |

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
