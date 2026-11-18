# Confirm localized RAW guides against two rail boundaries

Recorded: 2026-11-17T19:54:36-08:00 (America/Los_Angeles).

The localized donor replay holds the selected brackets fixed and
compares whole patches with smaller windows. Refining a single
boundary excludes most single-step controls, but still accepts
23/24 rail-only brackets. Fitting up to two parallel boundaries
inside each held-out check reduces this to 2/24. On the fixed
positive panel both refined fits retain 8.71% ISO400 and 0.87%
ISO6400 weak response under the respective quiet limits. Query
screening improves total query RMS while weakening response to the
faint direction. No training or new neural predictions were used.
[Exact-target report and frozen receipts](../docs/localized-donor-validation.md).

Both GFX scenes were reviewed at native size. The sky, building
and coarse fence match V120 with the two-edge check. Leaving the
V120 parent alone removes diagonal banding in the transferred
left cab crop. The fine mesh still lacks clear crossings.
[Train and platform](../docs/gfx-qualitative.md) ·
[Fine green mesh](../docs/gfx-green-mesh.md).

The 100k full-corpus run passed 64,300 updates. Its latest evaluated
milestone remains 50k. The donor replay contributes no standard
panel scores.
[Training milestones](../docs/full-corpus-scaling.md) ·
[Standard panel coverage](../docs/performance-history.md).
