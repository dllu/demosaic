# Start matched shared-edge weak-detail trial

Recorded: 2026-11-16T01:38:52-08:00 (America/Los_Angeles).

Started the existing frozen shared-edge recipe with the consolidated runner.
The V200 head, initialization, objectives, seed and full 1,000-row LR schedule
are retained. The audited intervention replaces 156 mixed rows with shared
edge/background pairs and adopts 844 other rows exactly; scene content and
coupling change together. No protected GFX pixels enter training.

The live review controller waits for this exact training process and completion
receipt. It will audit all committed row checkpoints, export raw/EMA endpoints,
evaluate the same 822 cached inputs as V200, pair metric rows by case identity,
and render the existing 60 boards/12 triplets with identical native160 pixels,
ROIs, exposures and contrast. All real families/profiles and flat/building
counterexamples remain present. Actual native viewing remains a separate step.

Added seven focused checks for case pairing, missing/duplicate/condition errors,
nonfinite metrics and exclusion of independent real references from exact-GT
comparisons; they pass, as does Ruff. The controller snapshots its sources and
uses the training snapshot for exports/inference. Existing receipts are intact.

[Launch receipt](../docs/results/shared-edge-launch-v1.json). At that observation,
both exact process identities were live and row 283 had committed, with 255 noisy
updates. This records execution progress, not a model-quality gain.

