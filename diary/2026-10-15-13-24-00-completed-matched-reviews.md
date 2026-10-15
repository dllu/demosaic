# Completed controlled reviews with native crop triplets

V18 joint and V19 refiner-only continuations completed 5000. All 202 sampled
input/target hashes, checkpoint RNG states, initialization and training source
hashes match. Known/unseen measured PSNR is 53.13418/53.12165 for joint tuning
versus 53.29175/53.10137 for control. Joint tuning gains synthetic-screen scores
but loses known-camera real quality. V19's full 427-photo PSNR/SSIM is
31.49630/0.923228, only +0.00830dB over V16. No candidate is promoted.

Native-target V20 and matched control V21 both stopped at 1000 as planned.
Measured PSNR is 53.25157/53.07420 versus53.27959/53.07429: no convincing gain.
The actual schedule contains 522 paired, 198 native-target and 280 existing-
synthetic batches; control has 522 paired/478 synthetic. All 34 logged shared
hashes match; 7 logged native substitutions differ. RNG states, common Python
training source, initialization and frozen restoration/EMA weights match.
The matched 64-photo screen is nearly tied. No model is promoted.

Both reviews include two native 160×160 triplets per candidate, with copied PNG
hashes and shared-panel equality checked. References are labeled AHD rather
than exact RGB GT. New real-suite receipts now carry checkpoint hash, noise
conditioning, WB and color matrix directly; older review crop metadata is
augmented from frozen prepared manifests without modifying source reports.
All 176 tests and Ruff pass. Protected final and personal GFX scenes remain
outside training. Full quality and speed goals remain open.

Next controlled question: whether native camera-linear targets help when the
restoration body can adapt, since the first pilot kept that body frozen.
