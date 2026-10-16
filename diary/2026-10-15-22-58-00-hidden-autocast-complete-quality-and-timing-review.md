# Hidden autocast review complete: tiny quality changes, lower observed time

V42 is an inference-only numerical-policy export from V37 EMA, with zero
training updates and every learned tensor unchanged. Source froze at a50ea37;
the controller completed at2026-10-16 05:50:11 UTC. The original/exported
checkpoint SHAs and canonical tensor SHA are in the export/review receipts.
No existing checkpoint or training recipe changes silently. The opt-in policy
casts only the first hidden encoder branch; native physical/head/final skip
and output precision remain FP32. Explicit FP32 inference is unchanged.

Known primary PSNR changes−0.00011513dB, unseen−0.00001047. Full427 photo PSNR
changes+0.00002134dB, source95%interval[−0.00000193,+0.00004636]; procedural
changes+0.00005074. Individual photo-case sRGB PSNR deltas span−0.025465 to
+0.036163dB, 1st/99th percentiles−0.002361/+0.002521. These are tiny numeric
changes, not bitwise equality, a perceptual equivalence proof or a new quality
gain. Same data/protocol/metric code and exact classical parity24/30 real pair
summaries plus37,212 synthetic rows gate cached V34/V37/V38/RawNIND reuse.

Ten native160 triplets are copied by SHA, with exact noisy/reference panels and
matched metadata. Every restored preview differs from cached V37 by at most
one8-bit display code; foliage/fence look consistent with the original, including
its remaining fine-detail softness. Two exact synthetic GT triplets per new
report are included; real AHD and separateISO100 references are not exactGT.
Both new full8746×11662×3 RGB16 files pass SHA/size, dtype/shape/16-bit tags,
sampled codes and sRGB ICC checks.

Actual learned V37/V42 CUDA/FP16 probes cover five analytic native64 patches at
four CFAs, ADC16/black.03/zero shot/read. Native ramp retains806 output codes
for both policies. Both respond to a one-code input offset; one-code-wave
prediction RMS distance is5.34e-9. These are precision checks, not lossless
reconstruction or real-scene performance claims. All329 tests pass in28.09s;
Ruff passes. Original full/packed paths and FP32 behavior stay compatible.

The first resident-warmup-only full-frame ABBA run varied substantially
(original32.11/26.62s). This justified a new run with one excluded FULL-frame
warmup per policy, then ABBA/BAAB, four measured runs per policy. No CPU tests
or other owned GPU work overlap this benchmark. Other users' processes remain
untouched, and the machine is shared.

Warmed original times:32.41925,31.92938,25.25249,31.62107s (mean30.30555).
V42:27.49039,23.98717,23.46633,23.46343s (mean24.60183). This is18.82% less
observed mean time, with overlapping shared-machine ranges, not an idle optimum
or10-second result. Same101.995852MP cached RAF, tile512/overlap64/batch4,
shot/read/WB/matrix, FP16 neural/FP32 physical policy; decode/load/render/encode
excluded, tiling/packing/transfer/blending included. Original repeated sampled
outputs match exactly; variant RMS distance is5.79e-6 cameraRGB. The complete
v1/v2 logs, executed scripts and source identities remain archived. Do not use
different-day timings as a controlled speed comparison.

`docs/hidden-autocast-v42-review.md` publishes the complete result and native
crops. README retains V34 representative images and links the explicit V37
export review. No owned training/evaluation/benchmark job remains running;
Commons download continues under its existing lock.

The active objective is not complete: decisive real/RawNIND/SOTA quality,
current-architecture trained DINO ablation, protected-final assessment and the
10-second target remain unproven. The current quality limitation deserves the
next major effort. In particular, the native clean corpus still has only31
original scenes (37 with the six-source opt-in extension); a larger audited
freely licensed low-ISO native corpus would be a more substantial diversity
test than the small extension. Preserve all protected/GFX scene exclusions.
