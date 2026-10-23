# Merge linear DNG export and opt-in Bayer hot-pixel repair

Recorded: 2026-10-22T23:13:52-07:00 (America/Los_Angeles).

Merged `feat/linear-dng-export` at `cf4635c` into current main after reviewing both commits. The only conflict was the documentation index: retained the current V101/V102 model guidance and added the exporter link. The branch adds camera-linear RGB16 DNG export, native edited JPEGs and adapted darktable sidecars, plus optional isolated Bayer hot-pixel repair before model inference. Original images remain read-only. Hot-pixel repair remains off by default; no model weights or existing comparison protocols changed.

CPU validation: 66 tests passed in 4.14s; two existing CUDA precision tests were skipped with CUDA deliberately hidden while V103 trains. Both darktable integration tests ran, including the complete RAW decode → restoration → DNG/JPEG batch and source-preservation checks. Independent LibRaw checks cover exact RGB16 samples, matrix/white balance and orientation. Related existing TIFF/inference/calibration/noise tests pass. Ruff and formatting pass for all six feature Python files, and the staged diff is clean.

The original V103 trainer, Commons preparation worker, source-overlap waiter, and planned evaluation/fullframe controllers stayed live with unchanged process identities. No model/data job was restarted for the merge. Current V102 comparisons remain published. Export validation is not a new model-quality or speed claim.

[Merge validation receipt](../docs/results/linear-dng-feature-merge-v1.json).
