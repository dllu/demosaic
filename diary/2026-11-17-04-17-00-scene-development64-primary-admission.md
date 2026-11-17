# Complete scene-context development review and admit canonical primary evaluation

Recorded: 2026-11-17T04:17:00-08:00 (America/Los_Angeles).

The previous goal turn made concrete progress: all three matched2k endpoints
were trained and actually viewed on both protected GFX families, canonical
photo crops were preserved in full-scene coordinates, and the64-source study
was launched. This turn closes that study and admits the complete primary
evaluation. The weak-detail/SOTA goal remains active and unresolved.

The [64-source report](../docs/whole-scene-context-development64.md) separates
training, numerical analysis and actual viewing. All128 cases/six variants
finish:3072 crop rows,752 new restoration/880 actual DINO calls,16 saved
predictions reused, unchanged frozen encoder. Source-balanced PSNR improves
about0.04dB versus V120 in every continuation. Spatial versus local-only is
−0.00321dB shadows/+0.00209dB ISO12800. ISO12800 quiet coarse luma/chroma error
falls1.993/1.238 scene-linear DN16, with source-tail sensitivity; overall color
and gradient errors increase slightly and weak-detail gains are unestablished.
Target-only quiet fine-error diagnostics penalize false grids. Preserve the
first failed orthogonality fixture; v2 fixes the boundary-domain assumption
without changing its tolerance. All eight selected native boards were opened;
rigging/branches/cloud/snow/brick detail still disappears. Both existing GFX
reviews use these exact checkpoints, and their missing fine crossings remain.

The [primary admission report](../docs/whole-scene-context-primary-admission.md)
binds every original five-argument input and photographic target. Physical-only
CUDA export qualifies all3162 batches with0 learned forwards;18 cached public
noisy RAW decodes match all162 camera crops. It ran briefly alongside training,
with the existing training PID/recipe/schedule preserved. Training wall time
was shared; no claim of bit-identical resulting weights under concurrency.
Actual heterogeneous-scene B4 composition and four-model frozen-feature replay
produce byte-identical outputs versus independent calls. The50 scene/data tests
and five replay tests pass.

Eight CPU-versus-GPU V120 probes expose one original quarter-DN failure on an
unclipped highlight value. Keep that result failed; channels-last does not fix
it. Saved-output analysis observes tiny scoring-domain differences, but does
not relax the bound. Recompute V120 with each candidate on the same CPU path;
all eight existing CPU predictions are adopted after byte-exact four-thread
checks. Preserve oneDNN SSIM JIT and JSON-coordinate failures. Only metrics
switch to reference convolution; neural policy and metric formulas stay fixed.

The actual three-case primary preflight completes, then the full CPU collector
starts under immutable source/plan and36h runtime bound. It retains full noisy
fields/features, uses checked identical frozen DINO reuse and adopts preflight
outputs without replay. These are admission checks, not completed broad scores.
The [PSNR history](../docs/performance-history.md) remains through V131, with
new full427/known-unseen scores explicitly pending. No scoped mean is promoted.

The [90,778-source training](../docs/full-corpus-scaling.md) remains live: fresh20k
control has passed6000 updates; long100k retains its immutable first1000 state
and resumes the remaining99k after the control. Neither full horizon has closed,
so endpoint scores/triplets/both fence reviews remain pending for scaling.
Do not restart on an observation timeout or reset source order/Adam/RNG.

Updated current-model/experiments/research/navigation and both qualitative
review maps, preserving historical receipts and README's concise recommendation.
Exact sources/failures/native pixels are published with independent saved-output
verification. No new history point is eligible yet; native/GFX coverage is
complete for the2k context endpoints, not the unfinished scaling trajectory.
