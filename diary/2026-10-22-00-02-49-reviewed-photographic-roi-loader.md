# Prepare reviewed photographic ROI sampling

Recorded: 2026-10-22T00:02:49-07:00 (America/Los_Angeles).

Added an opt-in photographic ROI reader for the six inspected training regions.
The default fraction is zero; no production recipe enables it. Selection uses
an independent deterministic stream before cache loading. It loads only the
chosen source, confines the crop to the recorded bin4 region, applies existing
geometry and finishes with area2. Flat/synthetic shares and selected-domain
loading remain unchanged. The fraction is conditional on a photographic
Commons sample; source and field-of-view distributions both change.

Catalogue validation binds exact training membership, manifest/cache identities,
aligned512-pixel context, dtype/shape and raw crop/area2 hashes. Training snapshots
catalogue bytes and SHA256; resume rejects a changed fraction or catalogue.
The catalogue's target hash describes its reviewed unaugmented view, not every
augmented training tensor.

All141 focused tests pass, including28 ROI tests. The actual tiny CPU trainer
matches uninterrupted4 steps to stop2+resume2 exactly for model, EMA, Adam, RNG,
best and step. The tests perform small-model CPU training; they use no DINO or
GPU. Ruff and format checks pass.

A separate CPU-only real-data proof uses the actual first24 domain decisions
and loads only the14 selected Commons steps:224 clean samples. Disabled tensors
all match the archived V95 reader bit-for-bit. A probe fraction0.5 selects62
reviewed regions across all six sources; the other162 outputs remain exact.
Each photograph loads one selected cache; procedural samples load none.
Python/NumPy/Torch global RNG stays unchanged. Six actual tensors match across
single-process and two spawned-worker loading; both owned workers exit.
This clean-data proof runs no model, optimizer or sensor-noise simulation.

The [readiness receipt](../docs/results/reviewed-ROI-loader-CPU-readiness-v1.json)
has SHA256 `115962c9c695e28ceb589f57daffd0ef81a4bde7b30821f75e612a31ba83cb77`.
The new source archive contains48 numerical files:45 unchanged parent files,
changes to data/train, and the added ROI module. Model/forward sources remain
byte-exact. All three existing plan guards pass; both frozen evaluation code
archives retain the original47 numerical files. The original main worker and
controller remain live on the photo panel, and the secondary native controller
continues waiting for their full exit. No new GPU job or frozen input change.

Documented configuration, sampling semantics, provenance and limits in the
[pipeline guide](../docs/training-pipeline.md#reviewed-photographic-regions).
There is no ROI-trained quality result or model promotion. V43 remains the
working reference; full project quality and speed goals remain unmet.

