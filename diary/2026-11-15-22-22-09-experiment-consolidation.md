# Consolidate experiment runtime and compose retained model stages

Recorded: 2026-11-15T22:22:09-08:00 (America/Los_Angeles).

The user requested the consolidation proposed after the project-status review.
Moved sixteen reusable script implementations into `demosaic.experiments` with
legacy module aliases. Added shared artifact/snapshot/runtime/cache/checkpoint/
training/evaluation code and a configured CLI. Named model presets and explicit
matching/pooled/innovation stages replace trial inheritance during new forwards;
historical constructors and tensor names stay at the compatibility boundary.

The pre-existing shared-edge data/preparation/tests are integrated. Their
original bytes were backed up under `.cache/consolidation-20261115/preexisting/`.
The original blank November 8 diary entry remains unchanged. The completed
shared-edge cache is bound by a prepared new plan at
`.cache/experiments/shared-edge/plan.json`; its 1,000-row audit reports 900 noisy
updates, 100 ADC skips, 3,600 images and 1,518 coupled pairs. Production training
was not launched and model quality is still unmeasured.

Validation: 427 tests across 27 affected modules pass; Ruff and wheel import/
package-content checks pass. Composition exactly matches saved V200 raw/EMA
predictions on a native64 cached crop, plus all-CFA outputs, auxiliary fields,
ADC routing and gradients in focused tests. The first eight original V200 CUDA
rows reproduce all 643 head parameters, EMA, Adam, CPU and CUDA RNG bit-for-bit
at seven updates/one skip. A discarded four-row CPU fixture completes the real
CLI's prepare, stop, resume and EMA export path. The focused tests also recover
a committed row after a reporting failure without replaying its inputs.

Two integration issues were fixed during validation: frozen packages must
resolve the enclosing checkout rather than treating their source snapshot as
the write root; the root generated `data/` ignore rule must be anchored so
packaged data-builder modules enter wheels. Failed local fixtures and original
receipts remain available; final v2 CLI/export checks pass.

All 107 original library files and 4,245 existing result/evidence files remain
byte-identical, along with the timezone correction map. Current docs now show
supported choices, limits and commands; full former indexes live under
`docs/history/`. Existing noisy/restored/GT crops, protected GFX references,
checkpoint identities and machine receipts remain intact. V120 remains the
general recommendation; the unresolved mesh/color/quiet-field tradeoff remains
scientific work, separate from this engineering change.

[Validation receipt](../docs/results/consolidation-validation-v1.json) ·
[CUDA replay](../docs/results/consolidation-v200-CUDA-replay-v1.json) ·
[Architecture](../docs/architecture.md).
