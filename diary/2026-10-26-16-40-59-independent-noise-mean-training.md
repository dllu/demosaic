# Implement independent-noise conditional-mean training

Recorded: 2026-10-26T16:40:59-07:00 (America/Los_Angeles).

Implemented independent sensor-noise pairs and a convex mean-prediction
reconstruction objective. Commons/native targets retain the actual unclipped
sensor signal and ADC metadata; each selected batch loads and augments 16 unique
targets once, then generates 32 sensor observations with identical geometry,
camera, CFA and shot/read settings. The second draw has its own deterministic
generator and preserves the original view/RNG. Real paired captures keep their
existing 16-observation path. Source-loss diagnostics inspect the first view
once per unique target; validation and inference stay single-view.

V124/V125 use the same V120 Small EMA initializer, cleaned90,784-source/twenty-
region cohort, paired32/native128 catalogues, seed67 and prospective20,000 fresh
updates. Their only loss difference is mean weight0 versus.25. Zero PSF,
geometry-before-area2, weak.15, photo attenuation.25, ROI quota.05, epsilon
.0003/paired.0001, band0 and LR1e-5/warm200 remain fixed.

All four discarded CPU128/B1 FP32 and CUDA256/B16 BF16 checks passed16+2 valid
resumed updates, with exact first18 input matching between arms. Eight changed-
weight/view-count resumes were rejected before construction. Model/EMA91 and
AdamW89 states are finite at18. Actual hardware-check counts:72 root/encoder/
optimizer steps,612 unique contexts and1,190 sensor observations. The175 tests
cover default behavior, loss/gradient equivalence, real-pair routing, source
tracing, actual resumed training, endpoint verification and receipt adoption.

The first controller's64GiB headroom requirement became unnecessarily restrictive
after the measured control peak of12.3GiB, with RAM stable near60GiB. Prepared a
new immutable controller plan adopting the three completed checks byte-for-byte;
only the unstarted CUDA candidate launch floor changed to56GiB. Its original
worker/source/config/parent/data,24GiB allocator cap,32GB runtime floor, full-run
64GiB launch floor and48-hour worker budgets are unchanged. Interrupted only
this experiment's waiting controller and four empty downstream waiters, and
rebound new queues to the replacement owner. The handoff script needed fixes
for asynchronous SIGSTOP delivery and a nullable child identity; both attempts
are retained, with no new worker/model calls. Old plans/receipts/logs remain.
The original V122/V123 training and review owners were never signaled or edited.

NumPy-only review inspected301,396,702 saved array values,289 matching target/
profile pairs and36,208,640 variance values exactly. It used no Torch, new noise,
RAW decode or neural calls. The actual checks and audit source are retained in
.cache/current-quality-20261023-v1/conditional-mean-training-v1/run; the current
controller lives in conditional-mean-training-v2/run. Full training waits for
the original V122/V123 train/evaluate/audit/report/mesh chain. Full endpoint
predictions, independent CPU audits, native GT triplets, all six main GFX crops,
RGB16 exports and both fixed green-mesh priors are queued in the V124-V125 v2
roots. Existing controls are reused, without neural reruns.

Verified the user's corrected fine-mesh reference is cached DSCF3835 ISO100,
f/5.6,2.5s with its camera JPEG; DSCF3842 stays the noisy capture. The main
3879/3880 test is unchanged. No original source media were opened this turn.

[Current implementation and execution](../docs/conditional-mean-training.md) ·
[Immutable setup/check evidence](../docs/results/independent-noise-mean-training-setup-v1.json).

V120 remains recommended. V124/V125 quality, SOTA and broad real-camera
superiority remain unproven; no improved-model performance claim is made here.
