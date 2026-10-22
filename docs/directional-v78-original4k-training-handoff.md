# V78 completes its original training budget; V79 is running

Current architecture and recommendations: [current model guide](current-model.md).
The versioned study below retains its measured results and original protocol.

V78 completed all 4,000 planned updates and its worker exited successfully.
V79 then started from the same genuine V63 EMA with fresh optimizer/EMA/RNG,
as specified in the [fixed study](directional-interval-v78-v79.md). Final quality
review waits for both arms. V43 was the reference for this experiment.
[Checkpoint hashes, retained states and handoff evidence](results/directional-v78-original4k-training-handoff-v1.json).

The V78 final checkpoint SHA256 is
`26e43921d2f4f46b39d9385c8399699f9fe1f0294f34efa4e6da0d4ad9baa7c4`.
The retained step 4,000 hard link has identical bytes. All 99 model tensors,
99 EMA tensors and 97 AdamW states pass finite/counter/shape checks. The four
scheduled checkpoints remain retained; every new branch parameter has nonzero
optimizer moments at each boundary. V78 processed 64,000 example draws, with
161 logged training records and 176 sampled legacy/input fingerprints. These
counts do not imply unique-source coverage or convergence.

Actual initial common weights match the genuine parent EMA exactly, and the
new output heads start at zero. The initial local branch hash matches the
production-size preflight. The frozen official DINO hash stays unchanged:
`370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd`.
The original manifests, source bundle, loss recipe and 4k horizon remain intact.

V79 passed the same common-weight/zero-head initialization hook before its
first logged update. Its first 16 sampled observations match V78 exactly in
step, domain, legacy batch hash, input hash and physical-target presence. The
first full observation fingerprint and common LR also match. The complete
176-sample and initialization-capture comparison remains pending until V79
finishes; no whole-trajectory equality is claimed now.

## Observed GPU process variation

The first logged total-loss difference is 0.0009739082306623459. The added
weighted interval term is 0.0009720364585518838, leaving about 1.872e-6.
The existing base terms themselves differ: rebuilding them in FP64 from the
logged linear/rendered/gradient/highlight/sensor terms gives a 1.873e-6
difference. Each reconstructed total agrees with its own logged loss within
6.52e-10, consistent with the original FP32 summation.

Thus the loss accounting is consistent while the first-step base loss terms
differ across these fresh processes. The prediction tensors were not retained
at this first step. The frozen
trainer enables cuDNN autotuning; its role in this difference has not been
isolated. This observation does not diagnose a specific kernel or predict the
eventual quality difference. The earlier
[unchanged-control replay](control-training-repeatability.md) also recorded
small first-step differences, under a different recipe; it supplies historical
context rather than an uncertainty estimate for this study.

The final V79-minus-V78 result describes the nominal interval intervention with
this procedural variation still present. Source/scene bootstrap bounds estimate
evaluation-source variation, not training-seed or process variation. The fixed
numerical criteria and required native/visual review remain unchanged. Neither
run is restarted or extended to chase repeatability.

This report verifies training completion and handoff. It contains no final
restoration-quality score, new full-frame output or speed result. The queued
primary/color/analytic/GFX and independent/native/publication checks remain
required after V79's original 4,000 updates.

## Trained EMA portability and actual interval routing

A CPU check now verifies the trained V78 EMA through the public inference
loader. All 99 restoration tensors, including the eight trained directional
tensors, load exactly from the saved EMA. An EMA-only inference copy produces
bitwise identical FP32 outputs to the full training checkpoint on four generated
64×64 sensor fixtures, one per Bayer pattern. The fixtures include signed black
samples and ADC-white patches; they contain no photographs, GT or quality
scores. Registered parameters/buffers and Torch CPU RNG remain unchanged during
forward, and both models use the same pinned cached official DINO weights.
CUDA stays uninitialized. This is an inference-portability check rather than a
full-frame, speed or 16-bit-export result.

V79's step 1,000 checkpoint also passes its 99/99/97 state audit. All 25,800 new
scalar parameters have nonzero optimizer moments. The first 56 sampled
observations and 41 logged step/domain/LR/full-batch hashes match V78 exactly.
Among those 41 logs, the 18 Commons/procedural and 12 native synthetic rows
include the interval term; all 11 paired rows omit it. Rebuilding the total loss
with independent NumPy FP32 operations exactly reproduces all 60 nonpaired
logged losses across the two arms' first 1,000 updates. These checks verify
training behavior without inspecting evaluation scores or changing the recipe.

[Inputs, outputs, source snapshots and first1k receipts](results/directional-portable-and-V79-first1k-v1.json).
Final restoration quality remains pending.
