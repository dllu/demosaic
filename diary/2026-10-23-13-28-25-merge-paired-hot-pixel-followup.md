# Merge paired hot-pixel follow-up from linear DNG branch

Recorded: 2026-10-23T13:28:25-07:00 (America/Los_Angeles).

After committing/pushing the completed incoming-source review as `2a3ba41`,
the branch ancestry check finds one additional feature commit beyond the
earlier linear-DNG merge: `4381fc23b6e4dc6245d201abb0d6e929dae38f14`.
Merge it into current main without conflicts. It adds explicit
`--hot-pixel-clusters`, covering paired same-phase defects and diagonal green
pairs while preserving corroborated multi-color lights and continuing lines.
The original isolated mode remains available, with correction off by default.
The CLI message now describes both modes accurately, and the current DNG
example uses V102 consistently in its checkpoint and suffix.

Actual merged-checkout validation passes all 42 focused tests in 5.42 seconds:
`test_hotpixels.py`, `test_hotpixel_clusters.py` and `test_dng.py`. The tests
exercise all four CFAs, both pair geometries, strip invariance, unchanged
inputs, noise/line/light controls and complete CPU DNG/JPEG exports with each
CLI switch. No tests are skipped. Ruff lint and formatting checks pass on all
five affected Python files. The feature branch's historical diary and its
earlier study evidence retain their bytes; the current doc records this
merged-checkout validation separately.

The original V104 run and all three evaluation/export/detail queues continue
on their frozen source and inputs. The new correction does not retroactively
change training or existing qualitative comparisons. The cleaned V109/V110
preparations and separate discarded CPU checks also retain their bytes.
[Merge record and frozen-plan checks](../docs/results/linear-dng-paired-followup-merge-v1.json).

Resume quality work with V102 as the best completed baseline while V104
finishes. Review V104's fixed endpoint and native comparisons before selecting
the initializer for the cleaned Tiny/Small trial. No capacity or new
model-quality conclusion follows from this exporter merge.
