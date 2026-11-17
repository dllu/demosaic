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
   placement. [Full primary collection is running](whole-scene-context-primary-admission.md).
   [Implementation](whole-scene-context-next-test.md).
2. **Test longer full-model training with broader data coverage.** Many possible
   crop/noise examples remain unused. Measure held-out learning curves at matched
   data, schedule and compute, including weak detail and flat-region errors.
   Failed small-head trials do not establish a full-model scaling limit.
   The [100k full-corpus continuation](full-corpus-scaling.md) has saved its first
   1000 updates, with shuffled epochs,5% reviewed quota and a fresh20k control.
   All3 context probes are complete; the20k control is running before the99k
   remainder. Quality is pending.
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
| [Whole-scene context test](whole-scene-context-next-test.md), [64-source review](whole-scene-context-development64.md) | All3 matched2k arms and64-source/intervention study complete/native-viewed; small quiet-coarse gains with detail/color costs, no convincing new crossings. Full427/camera collection running |
| [Full-corpus scaling](full-corpus-scaling.md) | Executing100k/20k matched-data continuations, source/crop/noise coverage and actual execution profile; no endpoint quality claim yet |

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
