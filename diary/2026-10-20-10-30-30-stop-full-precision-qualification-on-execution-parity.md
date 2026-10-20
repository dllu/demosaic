# Stop full precision qualification on execution parity

The three user-requested pipeline changes remain implemented and measured:
4x linear bin -> geometry/PSF -> final area2; only selected domains load;
repeat end-to-end sweeps retain batch16 (batch32 only1.3% faster at roughly
2x allocation). The matched geometry trial gains.50990dB on all427 photos.
No new batch/data/quality claim replaces those results. See
[training pipeline](../docs/training-pipeline.md).

Prepared a separate full paired FP32/hidden-FP16 qualification after the
completed mature pilot: original byte-exact V43/V63 checkpoint snapshots,
all427 photos/16 procedural sources/7 conditions/4 CFAs, known/unseen162
prepared crops, full448-label analytic and1176-color grids, standing GFX
contexts and two highlights. All1879 inputs/350 files are frozen under
plan aa076e39113bec7b24a8f1c5816f747a069cfcb7e04842d9cd0c0d91fb428da3.
The prospective protocol keeps every individual loss, strict flat-field
RMS limits without floors, and132 actual native cells before interpretation.
It forbids automatic full-frame continuation or default/export changes.

The focused gate/native metadata/policy tests pass20/20. The genuine CPU
proof finishes102 actual forwards:51/model (50 hooked plus one direct FP32).
It covers two fixed eligible photos and one procedural at native64, both
noise conditions and all CFAs/policies. Direct controls are byte-exact;
state/config/parameter/RNG checks pass and CUDA stays uninitialized.
This is engineering execution, not CUDA/quality evidence.

The CUDA preflight stops at the first V43 B4 GFX hidden-FP16 output. Against
its saved matching-policy pilot output the four maxima are
.64794/15.74976/4.43939/10.92171DN16; three exceed the fixed1DN16 maximum.
All four RMS differences remain below.25DN16. The paired FP32 output passes
(max.0468743DN16/RMS.000526482 over3,145,728 values). The original worker
asserts before saving its failed half prediction; traceback differences and
successful FP32 array remain. The checkout writer now saves an unfavorable
array and labeled progress before raising. The frozen run is untouched.
There is no original failed-GPU end-state receipt. Both exact owners exited;
no full quality worker or100MP restore ran and no automatic retry occurred.

A separate bounded four-arm diagnostic (plan
ffb8bda14416a65f70674a6b17b50ff61d8c072f2c7af71d0559dc536f452700)
finishes34 actual forwards/136 policy observations. Fresh serial processes
test paired/autotune, the original three-policy warmup sequence, benchmark
False, and original warmup plus inference-mode loading. Every repeat within
each process is byte-exact, but none restores pilot parity: hidden-FP16 maxima
are15.74976/15.74976/15.34742/15.74976DN16. FP32 maxima stay0/.04687/.05859/0.
Both history arms' ordinary FP16 maxima are15.17164DN16. All diagnostic
state/DINO/config/parameter/input/RNG/boundary invariants pass. The source
model modules and precision helpers match the pilot exactly. These checks
do not isolate the cause; within-process repeatability cannot establish
cross-run pilot parity. All diagnostic owners exited successfully.

An independent CUDA-hidden NumPy64 auditor recomputes all106,954,752 saved
RGB values, matching-policy differences, repeat differences and SHA/byte
identities with zero scalar disagreement. Its executed source is frozen at
465c7eae1b5aac1ecb778662ec4d7274211ce3611282bb9373b9d629224d2795.
All34 diagnostic outputs, including mismatches, remain saved.

[Stopped-run evidence](../docs/results/mature-hidden-FP16-full-quality-preflight-v1.json),
[independent audit](../docs/results/mature-precision-execution-independent-audit-v1.json)
and [protocol/current conclusion](../docs/mature-hidden-FP16-full-quality.md)
record the result and hashes. No limits are relaxed and no qualification,
full-population quality gain or new whole-photo speed is claimed. SOTA,
decisive real-photo superiority and100MP/10s remain unmet/unproven. V43,
README and production source/defaults stay unchanged. PROMPT.md is untouched.
