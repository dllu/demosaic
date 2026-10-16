# Rank4 adaptation loses its first gate; prepare a data-only trial

V49 finishes1000 updates and complete paired/full427/procedural/fullGFX review.
All41 logged input/target observations match V47, source bytes are exact and
new low-rank EMA tensors are learned. Versus V47: known primary−.00232dB
[−.01185,+.00664], unseen−.05029[−.06923,−.03303], photo−.01790
[−.03223,−.00264], procedural−.24361[−.65227,+.00789]. These are source-bootstrap
intervals from one seed, not training-seed intervals. A tiny photo SSIM increase
does not offset the primary/photo losses. Reject this recipe at this first gate;
do not generalize the rejection to every possible low-rank training recipe.

Published10 new native triplets and reused10 verified V47 triplets. Source/ROI/
conditioning/display and noisy/reference pixels match. Exact protocol, complete
evaluator source and24/30/37,212 classical records verify cached-control reuse.
Native inspection finds fabric smoothing and close GFX foliage/fence behavior,
with no decisive gain. Two full102MP RGB16/ICC outputs verify. Restoration took
35.10s on the shared machine; this is neither a repeated speed comparison nor10s.

Actual-trained CUDA analytic checks for V47/V49/V43 step2000 retain finite FP32
outputs, one-code responses and807/816/805 native ramp codes. They establish
weak-signal execution/code variation, not unbiased16-bit reconstruction quality.
The source and checkpoint identities are archived. V43 stays the reference.

The reviewed Commons extension's4× producer is still live and has passed8,100
new training caches without failures. The next V50 recipe changes only Commons
training membership40,170→52,536, retaining original frozen DINO/rank0 and all
other V47 settings. Its guarded queue will require the completed reviewed4×
freeze,10,558 new checksum verifications and actual V49 exit. Paired/native
observations must remain exact; Commons changes are expected. No gain is claimed.
