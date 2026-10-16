# Prepare a matched fresh DINO control while the corpus runs continue

V37 has completed its second 1,000 updates; V39 is training next. The sequential
controller remains PID1038531. No additional owned GPU experiment overlaps it.
The 30-triplet publication driver for its second-gate report is prepared and
will reject missing or mismatched evaluation artifacts.

Prepared V44/V45 for the missing trained DINO ablation of the current pipeline.
They start from the original verified Gaussian RGB weights rather than any
DINO-trained JDD parent. Same seed48, batch16, LR1e-4/planned10000, first1000
review, complete Commons4/native128/paired mix, physical/GAT settings and original
arithmetic. Only context presence and run destination differ.

CPU preflight verifies exact equality of all66 shared state tensors, zero DINO
gate, frozen genuine pinned backbone, and identical initial predictions across
all four CFAs on a native32px fixture. Its first forward correctly refused an
omitted explicit shot/read profile; the preflight now supplies the matching
physical profile and passes. No production code changed. Ruff passes.

[Recipes, procedure and limitations](../docs/fresh-dino-ablation.md) and
[machine-readable preflight](../docs/results/fresh-dino-ablation-preflight.json).
These recipes are prepared, not trained. Finish the live corpus continuation
and review before choosing the next GPU work. Its results and any ablation
must retain native noisy/restored/GT triplets and accurately labeled GFX crops.
