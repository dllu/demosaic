# Independent aggregation audit while original B continues

Previous turn made progress: completed S10k/cached CPU crop review, ten native
PNGs and provenance were committed/pushed as 6333669. This turn verified actual
controller 164667 and B trainer 300610 creation identities/liveness before work.
B was at 4,025 with finite loss; the workflow remains training-to10000. Downloader
3989567 also remains alive. No GPU job, restart or training-policy change was
introduced.

Added `scripts/audit_fresh_dino_statistics.py`. Independent standard-Python/
NumPy arithmetic reads saved case scores without production statistics imports
or PyTorch, checks full method/source/condition/CFA coverage, duplicates, core
metric finiteness and identical optional-metric support across methods. It
rebuilds group/source means and counts, real crop→capture→scene weighting,
all paired differences and the declared 1000/seed42 source-bootstrap percentiles.
It refuses an incomplete workflow and existing output.

Actual historical 3k execution `/evaluation/fresh-dino-statistics-audit-3k-v3`
verified 99,232 synthetic + 576 known + 720 unseen case rows, 592 group rows,
32 overall rows and 336 paired comparisons. Largest arithmetic difference is
1.4210854715202004e-14. This confirms aggregation of saved scores, not metric
computation, inference, visual quality or training-repeat uncertainty.

Initial scratch run v1 stopped on a mistaken assumption that the real model
receipt listed both RawNIND gain variants separately; it actually has one
publisher-weight receipt. Corrected expansion matches the two actual labels.
V2 passed, then v3 additionally required common optional-metric validity and
two-element intervals; full v3 passed. Final source is archived. Nine actual
negative checks reject duplicate/missing cases, missing primary value, altered
mean/CI, empty CI, missing comparison, method-dependent optional validity, and
the incomplete live 10k workflow. No premature 10k result was written.

Published audit note/receipt with input hashes and links to the unchanged 3k
native quality report. This prepares the 10k arithmetic check without claiming
its pending results are complete. Existing quality decisions/README remain.
Actual complete saved-case execution, negative checks and Ruff validate this
script-only change; production package/live frozen files remain unchanged.

Final liveness check: B at4,750 with finite loss; all193 logged observations
match the none/S prefix. Original frozen source and every pinned evaluation
file still match their expected hashes.
