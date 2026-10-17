# Reusable analytic summary check before V67 quality review

Previous goal turn was progress: added the genuine pinned GALOSH CPU reference,
independent checks and actual12-native serial review, committed/pushed9fbd30f.
Revalidated the actual V67 trainer/controller and all three review owners at this
turn's start; V67 advances1650→1925 on the unchanged original10000 schedule.
No model/source/data/recipe changes and no extra GPU work.

Moved the earlier V66-only analytic coverage/arithmetic procedure into a reusable
CLI, scripts/audit_analytic_summary.py. It checks the complete declared448
observations per method (carriers/flats,2 conditions/4CFAs/4draws), unique cases,
metric field sets/finiteness, complete groups and population mean/std/min/max with
independent math.fsum. Counts derive from checked collections; it does not reuse
old descriptive counters. Optional exact checkpoint identity binds a one-model
report. Scalar coverage/aggregation only: no per-case metric recomputation from
unavailable full predictions or inference is claimed.

Executed against actual V65 and V66 reports: both reproduce their published
896cases/2methods/56groups/1504fields and maximum arithmetic error exactly.
Six in-memory negative controls reject duplicate/omitted cases, nonfinite data,
a missing case metric, a changed summary mean and duplicate candidate labels.
Original reports remain untouched. CPU receipt is retained externally and in
`docs/results/analytic-summary-audit-cpu-preflight.json`. Ruff passes. Unchanged
neural model suite was not rerun. Use the verified CLI when V67's completed
analytic summary is saved; full quality/native review remains outstanding.
