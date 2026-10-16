# Weak-texture response measured and a separate source candidate prepared

Previous goal turn was progress: completed/published matched paired1000 review,
preserved immutable checkpoints and resumed both original4000 schedules. This
turn confirms controller2939648 live; V53 finishes4000 and V54 continues. The
current frozenb62c996 training/evaluation code is untouched; Commons download
remains live. No checkpoint/README promotion or final-test scoring.

Actual genuine CPU FP32 response probe:12 exact neutral horizontal sinusoids,
two conditions/four CFAs/four draws,384 observations/2304 method cases. Compare
V43 retained, fresh no-context/DINO-S3000, RawNIND channel, Wiener7 and MHC.
Signed carrier/DC/quadrature/noncarrier measurements separate lost contrast
from noise. V43 level.18/2%/ISO12800 gains.0024/.0133/.2410 for periods4/8/16;
10% gains.8613/.9738/.9570. ADC behavior is also content-dependent: period4/
level.18/2% gives no-context.0342 versus DINO-S.7015 and V43.3498. Period4 probes
CFA color ambiguity too. No generalized image MTF or restoration gain claimed.

Independent exact-input RAW fit:384 cases, four phase DC nuisances, known
background/carrier and clean-noise second moments. Approximate coherent-carrier
SNR16.31 at level.18/2%; oracle assumptions do not establish generic recoverability.
All rows replay exactly across input-only v1/v2. Four metric/covariance tests pass.
All ten native160px analytic triplets inspected and verified; plot and full
provenance published in docs/weak-texture-response.md. The probe writes complete
artifacts/completion line before command wrapper returns143; termination cause
after publication unisolated. Saved source/artifact validation passes; do not
claim clean CLI exit. No full neural rerun was performed.

New continuous weak fields: isotropic bandlimited/fiber modes, linear float32,
peak contrast.005–.2 and levels2^-8–.5; final-pixel frequency units. Private RNG,
no8-bit image. Seven generator tests pass. Actual32-sample512→existing geometry/
PSF→area2 CPU preflight verifies finite outputs, archived tensors and98.20–99.86%
RMS retention before augmentation. Runtime medians7.85/2.73ms generation under
concurrent load, not a training throughput claim.

Optional weak_texture_fraction defaults0 and replaces part of existing synthetic
quota; requires4×/2× pre-downsample recipe. Photos/flats/paired/native probabilities
remain unchanged; no discarded strong source is generated on weak draws. Resume
rejects changed procedural/flat/weak fractions. Actual frozen40170-source cache
seed52/native256:20 default samples matchb62c996 byte-exact, candidate changes only
the five declared replacement samples. Full CPU suite463 passed/8CUDA skipped
57.71s; subsequent11 training tests pass27.18s including all-weak worker-spawn
full/resumed model/EMA parity. No GPU tests overlap live quality training.

V55 prepared against V54 with identical retained parent,83-ID data, seed52/B16/
LR3e-5/planned4000 and all model/loss/noise flags. Weak.1 replaces half of
synthetic.2 Commons quota: expected5% of all patches. Quality training awaits
complete current4000 review. Genuine-parent CUDA preflight is implemented and
CLI/lint checked; first two Commons steps have0/2 replacements, so source guards
allow the unchanged first batch and require replacements across the pair.
No quality claim follows before that preflight and full matched review.

Primary research follow-up adds the older hybrid texture-acutance study and
AIM2025 RAW data/progressive-size context, with direct citations and scope.
The PROMPT objective remains active: broad real-photo superiority, SOTA,
protected-final evaluation and100MP/10s are still unproven.
