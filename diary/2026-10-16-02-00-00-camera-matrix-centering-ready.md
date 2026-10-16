# Retain camera information while testing better optimization coordinates

The previous goal turn made progress: current-data batch/GPU checks, selected
failure diagnosis and V46 measurement completed. This turn validates parent
reuse for V46: evaluator source hashes and24/30 real classical summaries plus
all37,212 synthetic classical cases match exactly. Ten native triplets match
source/ROI/noise/display and noisy/reference panel bytes. Two full RGB16 outputs
verify. V46 improves photo PSNR+.04855dB[+.01186,+.09280] and procedural
+.95118dB[+.24838,+2.06778], but loses known primary−.15660dB
[−.25273,−.01690] and unseen−.06112dB[−.14254,+.01410]. No promotion. Selected
photos/GFX look close; threads/cloud/leaf texture remain soft.
[Full review](../docs/camera-projection-v46-review.md).

Implement opt-in camera-matrix centering to retain all metadata. Matrices near
identity contain a large constant feature component. Instead of removing that
input, use a fixed parent diagonal reference so matrix gradients see M-I while
the initial forward and every common trainable tensor remain exactly unchanged.
The trainable bias handles the unconditional offset. Matrix entries, WB, CFA,
physical anchors and DINO remain available. No new trainable parameters.

Default false preserves the old path and state keys. The optional64×3 FP32
reference is derived only when initializing an older parent, saved in
checkpoints/EMA and never reset on resume. A centered checkpoint missing it is
rejected. Full/packed paths share the helper; no hidden precision change.

Six focused tests pass, including initial exactness, neutral-matrix gradients
with retained sensitivity to matrix deltas, fixed-buffer persistence, portable
loading and exact interrupted/resumed model/EMA/AdamW/RNG. The full CUDA suite
passes358 tests in27.81s. The genuine pinned V43-first1000 GPU preflight verifies
all common tensors and nine exact forward comparisons: all4 CFAs at3 noise
priors in FP32/BF16/FP16. Its2→4 update fixture preserves the reference in
model/EMA, AdamW step counters and exact portable EMA loading.
[Method/recipes](../docs/camera-matrix-centering.md),
[GPU receipt/source snapshot](../docs/results/camera-centering-gpu-preflight-v1.json).

V47 control/V48 centered share immutable V43 first1000 EMA8ee3, before the large
procedural regression, with fresh AdamW/EMA, seed50, batch16, LR3e-5/planned3000,
first1000 gate. Complete Commons4/native128/paired and original8 validation,
25/25/50 mix, pre-reduction geometry, pinned frozen DINO and original precision
stay fixed. No low-rank or hidden-autocast change. The initial prediction is
identical; only optimization coordinates differ. Shared logged hashes must match.

Next: freeze this source, train both sequentially to1000, verify all41 input/
target observations, then complete known/unseen, full427/procedural and full102MP
GFX review with at least two native exact-GT triplets per model. Current V43
step2000 stays the photographic reference. Initial equivalence does not prove
quality improvement. Broad RawNIND/SOTA margin and full objective remain open.
