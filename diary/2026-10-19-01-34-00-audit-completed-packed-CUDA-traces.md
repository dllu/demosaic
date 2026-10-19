# Audit completed V72/V73 CUDA traces while current review runs

The previous goal turn made concrete progress: actual emergency recovery
completed the original 4k budgets and tested cache recovery/handoff jobs were
queued. This continuation verifies the current review, closure and both data
waiters by actual PID/creation time. The quality worker is live and advancing
through full427. No timeout restart or criterion change.

Found that both earlier mixed16 packed GPU profiles had completed and exited,
while documentation still described a queue. The existing frozen trace reader
executed twice on CPU, requiring genuine CUDA activity and complete mappings;
both commands exited 0. A separate stdlib-only Decimal auditor independently
verifies every activity's CPU External ID, unique runtime correlation,
same-thread launch containment, innermost named range and all duration sums.
All 57 immutable trace/result/checkpoint/source/input references remain exact.
The independent auditor exited 0 without importing Torch.

No-DINO/DINO have 1,093/1,315 device activities, excluding 20/23 overlapping GPU
annotations. Six groups use 83.63%/74.54% of summed activity, with 75.32%/75.09%
of group activity in convolution. DINO context/backbone uses 10.82%. Separate
five-sample resident B4/native512 FP32 medians are 1120.04/1256.87ms. This points
future compute work at spatial groups without predicting full-frame speed.
Both models remain quality-rejected. No GPU probe, precision/default change,
training extension or promotion is introduced.

[Completed analysis](../docs/mixed16-packed-inference-profile.md) and
[source/trace/Decimal audit receipt](../docs/results/mixed16-quarter-CUDA-trace-analysis-v1.json).
