# Training on more of the corpus and improving throughput

Review: **2026-11-17, America/Los_Angeles**. Read-only findings and proposed
work; no training, profiling, model/config edits or changes to active experiments.
Repository HEAD at review was `90a24f7f`; another agent is implementing scene
data/model integration. This note supplements the
[context and production review](weak-detail-global-context-production-review-2026-11-16.md).

**The corpus supports a substantially larger full-model training experiment.
We have not established that its useful examples, or the model's capacity to
learn from them, are exhausted.** Batch-size saturation concerns examples per
second; it does not establish convergence as the number of examples increases.
The earlier 10× continuation of a small detail model is insufficient evidence
against longer training of the full restoration network with diverse crops.

## What the existing coverage audit actually shows

The [executed source-selector audit](training-source-schedule-coverage.md)
enumerates the V131/V132 20k schedule at batch 16:

| Quantity | Count |
| --- | ---: |
| All clean target slots | 320,000 |
| Commons photographic draws | 112,424 |
| Draws allocated to 29 reviewed sources | 56,256 |
| Other photographic draws | 56,168 |
| Distinct photographic source IDs | 42,086 of 90,781: **46.36%** |

Thus a 20k run is not even one ordinary-photo pass across this corpus. Half of
its photographic draws concentrate on a very small bank of reviewed regions.
These figures describe this continuation's schedule, not the model's lifetime
exposure through pretrained weights and earlier ancestors. Different crops,
camera transforms, exposure and independent noise still make repeated-source
draws useful; source counts alone cannot diagnose overfitting.

There is already a verified [shuffled photographic epoch sampler](photographic-epoch-order.md).
On the same-sized prepared corpus with a 5% reviewed quota, it covers all 90,778
sources within 20k steps, compared with 69.26% under replacement sampling. This
is implemented data coverage, not a demonstrated trained-quality improvement.
Use its existing reader/order machinery in a new declared run rather than
reimplementing it or assuming historical queued studies completed.

The user's crop argument is correct: revisiting a photograph with new spatial
positions, geometry, exposure and noise supplies many useful training examples.
We should track **source coverage, crop-location coverage and corruption
coverage separately**. Fresh noise on the same crop helps learn an expectation
over sensor noise, but does not add another scene layout. Overlapping crops
are correlated; that does not make them useless.

There is also a resolution qualification. The pipeline bins the original image
4×, performs geometry, then reduces another 2×. The current
[scene-data feasibility audit](whole-scene-context-next-test.md) finds only
1,759 of 90,781 cached sources with a short side at least 1,024 before the final
2× reduction. Thousands of stochastic augmentations do not necessarily mean
thousands of disjoint, native-resolution clean patches. Preserve the cleaning
benefit when testing more native detail; any bin4-versus-bin8 target change
needs its own matched data comparison.

## The larger training experiment I would prioritize

Run a **100,000-update full-restoration continuation**, initially retaining
V120's architecture and loss, with a declared broader sampling recipe and
fresh per-visit crop/noise draws. Keep the official DINO encoder frozen for this
first scaling test. Save 20k, 50k and 100k states; consider a 200k extension
if held-out detail/flat/camera curves justify the extra compute.

Choose the learning-rate horizon before launching. The present 20k cosine
schedule decays from 1e-5 to 1e-6; a small late improvement after that decay is
not proof of data exhaustion. Use a schedule intended for the longer run and
retain optimizer/EMA state across checkpoints. Do not restart a 20k schedule
or replay its source/noise sequence at each milestone. Save global draw index,
epoch permutation, crop/noise seeds and complete resume state.

To separate causes economically:

1. Use a matched 20k control for the chosen sampling recipe if no completed
   equivalent already exists. Keep architecture, targets and losses fixed.
2. Interpret 20k/50k/100k checkpoints from the single long run as progress under
   its declared long schedule. They do not isolate schedule length from compute
   when compared with a separately annealed 20k run.
3. Test added whole-scene context against a local-only arm on identical scene
   observations and crop schedules. The other agent's current context work
   supplies that path; do not attribute a simultaneous data/budget change to
   the new context branch.

Suggested source policy: shuffled ordinary-photo epochs, a modest reviewed-region
quota such as the existing 5% control, varied spatial sampling over repeated
epochs, and retained native/paired and genuinely flat examples. Expand the
reviewed bank before allocating a large fraction of all training to it. Keep
protected captures/JPEGs/siblings out of training and use local cached media.

At batch 16, 100k and 200k updates mean **1.6 million and 3.2 million examples**,
versus 320k now. Linear projections from the recorded 6.5–8.5-hour 20k runs are
approximately **32–42 hours for 100k** and **65–85 hours for 200k**, excluding
broad evaluation. These are GB10 planning estimates under historical execution,
not measurements of the new recipe, context model or RTX 5000 Ada.

## Specific pipeline opportunities found in the code and receipts

| Finding | Proposed action | What remains to measure |
| --- | --- | --- |
| V120 and V132 saved run configs use `deterministic-v1`. An [older controlled policy benchmark](training-execution.md) measures 21.58 patches/s in throughput mode versus 12.62 strict: **41.5% less throughput** in strict mode. | Qualify the existing throughput policy for a new large run; retain declared data schedules, physical precision and checkpoint provenance. Existing exact-replay studies keep their settings. | Current-model speed and training-quality variation. The older 1.71× time ratio is not a promised V120 gain. |
| V132's saved config has **zero workers** for all three loaders; V120 has two each. | Profile loader wait separately; test bounded worker/prefetch settings and worker thread counts on each host. | Actual CPU/IO bottleneck and resource contention; zero workers alone does not measure lost time. |
| [CleanDataset](../src/demosaic/data.py) memory-maps a cache for each selected source, crops/copies/converts it and performs geometry. Originals are already preprocessed. | Retain the existing clean caches. Test bounded per-worker mapping/cache reuse, locality-aware shuffled access or shards only if metadata/IO is significant. Cache source pixels, keep crop/noise randomness fresh. | Whether openings, random reads, augmentation or compute dominate; do not rebuild terabytes speculatively. |
| Loaders currently disable pinned memory; transfers in [train.py](../src/demosaic/train.py) are ordinary `.to(device)` calls. | Benchmark pinned staging and asynchronous prefetch on the discrete Ada, with bounded buffers; assess GB10 separately because it shares physical RAM. | Whether overlap improves throughput or simply adds copies/memory pressure. |
| The controlled [V131 resume wrapper](../scripts/resume_raw_spatial_trial.py) fingerprints full clean/prepared batches every update; `batch_fingerprint` copies GPU tensors to CPU. Logged metrics also extract scalars. | For a new throughput run, measure audit/synchronization cost. Keep manifest/seed/source identity and required checks; consider sampled full-tensor witnesses and batched logs rather than every-step GPU readback where exact paired-study receipts are unnecessary. | Saved seconds per update and sufficient reproducibility. Do not edit or weaken the historical study's contract. |
| B16→B32 gave only 1.3% higher throughput in an [older RGB sweep](current-pipeline-batch-sweep.md). | Sweep actual-model B8/16/32/64 on the Ada and GB10 at fixed shapes. Select examples/s and quality per wall time, not memory occupancy. | Each device/model's best batch and the learning-rate implications. |
| Dense DRUNet compute and repeated tile-DINO calls remain substantial. | After profiling, evaluate regional compilation/fusion; train the shared scene-context path and later a compact student as separate quality/efficiency comparisons. | Compile coverage, amortization and actual speed/quality. Existing packed-only compilation is not V120 compilation support. |

Saved configurations inspected:
`.cache/current-quality-20261023-v1/Small-paired32-weak-detail-training-v1/run/work/artifacts/train/V120/config.yaml`
and `.cache/experiments/raw-spatial-continuation-v2/work/artifacts/train/V132/config.yaml`.
These are actual executed settings, distinct from current mutable trainer code.

PyTorch's [performance guide](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
supports tuning data-loader overlap and avoiding unnecessary scalar extraction
and CPU/GPU copies. Those are candidates here, not evidence of measured speedup.
Training already uses mixed precision; enabling AMP is not a newly discovered
optimization. Preserve physical arithmetic and check weak-detail/color behavior
when changing numerical policy.

Do not cache one frozen DINO feature map per clean source and reuse it for every
corruption: the encoder currently sees an input whose crop, camera, exposure
and noise vary. That would change the learning problem. A shared scene encoding
is reusable across tiles of the **same noisy observation**, which is precisely
why the scene-data/coordinate contract matters.

## Spend more of the budget on informative training

Use a representative fixed monitoring set larger than the existing eight-image
panel, with weak-detail and flat-field measures reported separately. Add a
separate fresh-noise check at milestones. Monitor ordinary/camera quality,
phase-correct weak increments, coarse luma/chroma mottle and adverse color cases;
training loss or spectral response alone cannot choose the best checkpoint.
Keep source-level validation/test separation, and do not repeatedly tune against
the protected real references as though they were exact GT.

Run lightweight monitoring during training; run the broad retained suite and
native comparisons at useful milestones. Preserve necessary checks and original
receipts, but avoid making every progress snapshot another complete publication
pipeline. Compare **useful quality improvement per GPU-hour and total elapsed
hour**, including CPU analysis and human/agent review. New quality reports still
need two native noisy/restored/GT triplets and the standing real-camera views.

For each new larger run, record a compact table of actual source/crop/noise
coverage, examples processed, training/loader/validation/checkpoint time,
throughput and quality. That would answer whether we are limited by insufficient
training, sampling concentration, an expensive pipeline, or the representation.
The current evidence justifies testing all four; it does not justify declaring
the corpus exhausted or assuming arbitrary extra training will recover the fence.
