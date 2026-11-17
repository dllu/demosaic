# Separate current guidance from experiment history and refresh PSNR coverage

Recorded: 2026-11-17T00:29:47-08:00 (America/Los_Angeles).

The user identified fragmented README updates, stale general-looking galleries,
and an uncertain PSNR chart. The README was 330 lines; the research overview
was 901 lines. The chart stopped at V123 even though V131's full broad review
was complete. Several gallery openings still recommended V114/V115.

Reduced README to 77 lines with installation/inference, the V120 recommendation,
a short explanation of experiment IDs, two unchanged native triplets with
provenance, and navigation. Reorganized model choices, experiment status,
research priorities and the documentation index. Scoped the older cross-camera,
material, RawNIND and source-review pages; added current GFX review maps and
corrected stale training/endpoint links. The three-camera gallery still lacks
newer published models; no results were fabricated to fill that gap.

Archived the six previous entry points with rebased links and scope banners in
`docs/history/before-2026-11-17-cleanup/`. Preserved the previous chart in all
three formats and its generator byte-for-byte, with original hashes. The
historical chart page displays those archived assets. Original receipts,
comparison images, checkpoints, training inputs and frozen code remain unchanged.

Added V131's full427, known and unseen scores from the canonical independent
CPU-to-CPU audit and producer plan to a new versioned PSNR registry. All 56 old
points remain exact. Updated the generator/default registry and regenerated
PNG/SVG/PDF plus the score table. V132, later component trials and the ADC-only
repair do not acquire incomparable broad scores. The plot remains descriptive
history across unequal budgets, not a training curve or a release ranking.

Validation: all 57 endpoints rebuild exactly from their original source reports;
all source hashes and the archived plot/generator bytes match. Eight plot tests
pass; Ruff and diff whitespace checks pass. Checked 1,404 relative links/anchors
across updated guides and archived pages with no unresolved targets; inspected
the regenerated plot. The README's existing crop pixels were not regenerated.

Added `docs/documentation-maintenance.md` and a short AGENTS.md routing rule so
future agents replace the relevant status summary instead of appending the same
experiment narrative across entry points. Detailed reports remain evidence
snapshots, and the diary records historical decisions.

No model evaluation, training, profiling, original-photo reads, or experiment
process changes were performed. The other agent's untracked scene-context and
profiling implementation files were left alone.
