# RAW learning on a small production training set

The model fits the earlier simple generated example, but **learns little on a
varied 16-batch training replay in either BF16 or FP32**. This changes the next
step: isolate optimization behavior before spending another long training run
or attributing the weak restoration to inference precision.

[Curves, hashes, recipe and exact numeric summary](results/packed-isotropic-production-learning.json).
[Actual held-out quality and native crops](packed-isotropic-first32000-review.md).

The [completed 40k review](packed-isotropic-quarter-review.md) now confirms
actual longer learning: photo gains of2.061/2.188dB and camera gains of4.0–4.7dB
over the own8k boundaries. Both models still trail mature controls and retain
substantial grain. The complete numerical, artifact and selected-native review
is finished; neither model is promoted. The earlier short replays below do not
prove the architecture cannot learn.

This is an optimization diagnosis, not an improved quality model. All learned
weights are discarded. No held-out image, private photo or protected-final scene
is optimized, and no diagnostic state enters a quality run.

## Actual production observations

The fixture consists of the original recipe's next16 steps,8001–8016, at batch4:
64 training examples, seven Commons/procedural batches, four native-RAW batches
and five paired-RAW batches. Source selection, crops,4×→geometry/PSF→2× reduction,
camera/noise/ADC draws and production losses use the actual training operators.
Source IDs, sample indices, cache/fixture hashes and all batch fingerprints are
retained. Degradation runs once on CUDA; both precision arms receive identical
frozen arrays. The original training/validation/test membership stays fixed.

Each independent arm starts from V71's actual step8,000 **raw model and original
AdamW moments**, rather than EMA or a new optimizer. It performs512 updates,
repeating the16 observations32 times in original order. LR remains the saved
step8,000 value, weight decay.01 and gradient clip1. This constant-LR replay is
not a continuation of the original cosine schedule. Every gradient is present
and the global gradient norm is finite. Original Adam step counters reach8,512.

## Results on the replayed training observations

| Precision | Domain | Final/initial loss | Final/initial MSE |
| --- | --- | ---: | ---: |
| BF16 | Commons/procedural | 0.9383 | 0.8541 |
| FP32 | Commons/procedural | 0.9602 | 0.8684 |
| BF16 | Native RAW synthetic | 1.0235 | 0.9911 |
| FP32 | Native RAW synthetic | 1.0258 | 0.9941 |
| BF16 | Paired RAW | 1.0353 | 1.0250 |
| FP32 | Paired RAW | 1.0396 | 1.0225 |

MSE is against the fixed clean target for synthetic degradations; paired MSE
uses only valid measured reference-CFA samples. Paired low-ISO references retain
noise and are not exact clean RGB GT. Numbers balance batches within a domain,
not sources/scenes, and are training-set errors. They are not generalization
scores or training-repeat confidence intervals.

The similar failure in FP32 argues against a broad BF16-only explanation here.
It does not prove that longer training cannot work. The replay is small, has
repeated noise draws and contains mixed exposure/conditioning/loss regimes.
Commons MSE also includes clipped-highlight reconstruction; a drop there alone
does not demonstrate useful denoising on native or paired inputs.

## Narrower isolation

A separate serial experiment uses the same frozen observations and actual raw
weights. Its four BF16 arms are:

1. Optimize only Commons step8005, with original Adam moments.
2. Optimize only paired step8001, with original Adam moments.
3. Replay all16 with fresh Adam moments and the same LR.
4. Replay all16 after a fixed RAW parameter rescaling, with transformed original
   Adam moments.

The fourth arm multiplies the four RAW feature channels by4 and divides their
corresponding input columns in both physical stems by4. Adam's first and second
moments scale by4 and16. All other weights/moments stay fixed. Initial FP32
predictions must agree within2e−7. The represented initial function and capacity
are unchanged; optimization geometry and effective RAW-weight steps change.
This is not a precision correction or a production architecture setting.

The exploratory gain4 comes from a CPU measurement: on these paired batches,
the median RAW contribution RMS at the learned local stem is.2201 times the
metadata contribution. This describes feature units, not proof that metadata
causes the failure. Its initial transformation is actually bitwise equal in
FP32 on all16 observations.

| Isolation arm | Domain optimized | Final/initial loss | Final/initial MSE |
| --- | --- | ---: | ---: |
| Single Commons batch, original Adam | Commons/procedural | 0.7423 | 0.7033 |
| Single paired batch, original Adam | Paired RAW | 0.7627 | 0.7530 |
| All16, fresh Adam | Commons/procedural | 0.9643 | 0.8736 |
| All16, fresh Adam | Native RAW synthetic | 1.0759 | 0.9890 |
| All16, fresh Adam | Paired RAW | 1.0811 | 1.0092 |
| All16, RAW gain4 | Commons/procedural | 0.9528 | 0.8828 |
| All16, RAW gain4 | Native RAW synthetic | 1.0453 | 0.9807 |
| All16, RAW gain4 | Paired RAW | 1.0798 | 1.0399 |

Both single batches learn more than the mixture. Different sample counts and
contents prevent interpreting that as proof of a specific domain-interference
mechanism. Neither fresh moments nor RAW parameter rescaling offers a broad
improvement. No production loss, optimizer, feature-gain setting or architecture
is changed. All four sets of learned weights are discarded.

## Original quality trials completed the 40k boundary

The original8k boundary is only5% of its planned160k-update horizon. With no
identified finite-state/target/precision fault or supported simple replacement,
both original arms have completed the explicit **step40,000 review boundary**:160,000
examples, a quarter of the original640,000-example horizon. This is a decision
to measure actual longer learning, not a claim of convergence or stronger quality.

Each restored its own actual8k raw model, EMA, Adam moments, Torch/Python/CUDA RNG
and best-score state. The original160k cosine horizon, warmup2k, LR2e−4,
batch4/BF16, source bundle and frozen manifests remain fixed. New branch run
directories preserve the original8k logs, checkpoints and reports byte for byte.
No diagnostic weight is used. Intermediate16k/24k/32k checkpoints are retained;
there is no automatic promotion or continuation beyond40k.

The [completed boundary and handoff receipt](results/packed-isotropic-quarter-training-boundary-v1.json)
verifies that both training owners have exited and the independent full-state,
source, ancestry and observation audit has passed. The actual1602 logged
training observations per arm match in step/domain/LR/batch hash. Actual startup
checks verify model/optimizer/global RNG before the first update and EMA before
its first update; the first16 observations also match this replay fixture.
The quality workflow and selected-native review have now completed. Their
results establish own8k progress but not a promoted model; see the full review
above. Completed training alone was not treated as quality evidence.

Private status:
`/mnt/external/demosaic/runs/packed-isotropic-quarter-workflow-v1.json`.

The retained no-DINO24k checkpoint passes an independent
[CPU state/source/recipe audit](results/packed-isotropic-no-dino24k-state-CPU-v1.json).
All852 model and EMA tensors have changed since8k; all852 Adam states are finite,
with correct counters, shapes and nonnegative second moments. The reconstructed
source bundle, four manifests and962 logged training rows retain the original
recipe and LR schedule. This verifies state integrity, without inference or a
quality claim. That audit preceded DINO's serial continuation; both arms have
since completed40k.

## Frozen quarter-horizon review queue

The [queued protocol and CPU checks](results/packed-isotropic-quarter-review-queue-v1.json)
wait for the exact training controller and final child to exit successfully.
Both actual40k states must pass independent model/EMA/Adam/RNG/source/data and
full-history checks before inference. Active or incomplete training is rejected.
No GPU review overlaps the owned training.

The fixed panels retain648 known,810 unseen,111,636 full-photo/procedural and
2,240 analytic cases, full GFX RGB16 exports, three cached cameras, selected
colors and the same4,704-case hue grid. The9 primary model pairs are joined by
two own8k progress pairs:132 metric comparisons,33 classical witnesses and99
source sensitivities. Own progress reuses saved8k scores only after observation
metadata and all three classical controls match. This avoids rerunning the8k
networks and keeps longer-training progress separate from the DINO gap.

The hue stage makes2,352 new predictions for the two40k models and reuses2,352
unchanged V63/Nonlocal reference arrays. Actual CPU reuse verifies source,
weights, observations, precision, arrays, regenerated native previews and
descriptive groups, without CUDA or new inference. A separate historical-score
replay checks all132/99 statistics. Its history aliases are arithmetic fixtures,
not actual RAW ancestors or new40k quality results. Thirty-eight focused tests
pass, including incomplete/live-owner rejection and the special resumed log row.

The queue leaves visual inspection, performance-report crops, quality decisions
and any later continuation to explicit follow-up. It does not score protected
final scenes or promote a model automatically. The original8k report stays intact.

Private review status:
`/mnt/external/demosaic/runs/packed-isotropic-quarter-review-workflow-v1.json`.

A separate [fresh input-coordinate CPU diagnostic](packed-isotropic-fresh-coordinates.md)
now tests internal RAW feature scaling from identical fresh weights and a common
initial bilinear prediction. It reuses the same16 training observations and
discards all learned states. Its [64-update interim comparison](results/packed-isotropic-fresh-coordinate-CPU-interim64-v1.json)
finds no broad coordinate-map improvement; final results remain pending.
It yields CPU computation during owned reviews/timing and continues separately
after those owners exit; it does not change the matched trials.

The [completed four-arm CUDA residual-unit diagnostic](packed-isotropic-residual-units.md)
adds a fixed1/32 scale on the learned residual to the input gain32 arm. This
reduces early original-loss overshoot, but native/paired improvements over the
bilinear start are tiny and paired MSE remains above its start. All weights are
discarded, no production setting is adopted, and the CPU study continues.
