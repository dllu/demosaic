# Trace difficult training crops back to their sources

V120/V121 set `source_loss_every: 100` to append per-example Commons
diagnostics to `RUN/source-loss.jsonl` on the first update and every 100 optimizer
updates. Zero, the default, adds no source metadata or diagnostic computation.
This option has not been enabled retroactively in the frozen V119 run.
Both new arms passed actual16-update CPU/CUDA checks. Their source diagnostics
forbid neural Module calls and verify unchanged Python/NumPy/Torch CPU/CUDA RNG
states; V120 production is running, with V121 queued sequentially.
[Current controlled trials and launch evidence](paired32-weak-detail-training.md).

The [first actual Small-model source review](current-source-loss-review.md)
freezes128 diagnostic draws through update800, including95 distinct photographs.
Twenty-eight selected sources receive native inspection and are retained. The
review uses losses to find examples rather than treating high loss as a bad-photo
label; neither active cohort changes.

Each record identifies the actual photograph after exclusion retries or a
reviewed-ROI override: source ID, cache path and manifest-declared hash, cache crop rectangle,
reviewed region, dataset draw index/seed and augmentation reduction. Procedural,
smooth-field and weak-texture draws are labeled separately. These are coordinates
in the source cache **before** rotation, projective geometry and final reduction.
The saved run configuration/source archive and draw index define those transforms.
No additional random draws, source reloads or original RAW decoding are needed.

The logger scores the **existing prediction** with detached FP32 singleton
reconstruction losses. It uses the configured objective, epsilon, camera masks
and optional loss terms, and records shot/read, CFA, WB/matrix and supervision
shape. It performs no neural forward or gradient update. The ordinary model,
optimizer, EMA and loss/backward path remain the training path.

Singleton mask denominators can differ from batch denominators, so these scores
are **not additive contributions to the training loss**. High loss can reflect
strong noise, saturation, unusual colors or difficult real detail. Group by
noise/condition and repeated source draws before prioritizing native visual
inspection; never automatically exclude a photo for a high score. The metadata
supports locating a bad photograph, not proving that it is bad. Noise replay
also depends on the run's random-state/per-data-step policy; the draw seed alone
reproduces the clean source augmentation, not every noise realization.

Joined optimizer forwards preserve the original source-group and example order.
Paired/native batches are omitted from this Commons-specific log. Logging does
add FP32 loss work and synchronization at the selected interval. A resumed run
also logs its first resumed update, then follows the same interval; diagnostics
can therefore contain extra records versus an uninterrupted run.

The focused 50-test check covers actual exclusion/ROI selection, all procedural
families, unchanged source tensors/RNG, closed-form scores, no neural-module
calls, and actual single/joined mixed-domain training with resume. Model, EMA,
AdamW states and random states are bit-identical with logging on/off in those
CPU fixtures. This is an implementation check, not a trained-quality result or
a GPU timing measurement. Further corpus changes still require visual review.

[Implementation, test and actual native-reader receipts](results/source-loss-diagnostics-v1.json).
