# Centered RAW reconstruction prototype and serialized review work

The previous turn completed the V62 review and launched the longer matched
data stage plus new 4× cache preparation. This turn verified those exact owners
live; no trainer or producer was restarted. V63 remains on immutable c905 source
in the old worktree. Root source changes do not alter its pending V64 arm.

Implemented optional AdaptiveRawKernel: bilinear baseline plus learned signed
coefficients on same-color RAW differences at packed windows 1/5/17. Existing
DINOv3/RGB native features and normalized RGB condition 324 coefficients, adding
22,032 parameters. Constant calibrated camera RGB gives zero differences for
every term. Phase box means use separable center-relative differences so constant
FP32 phases remain exact, including borders. Final filtering stays IEEE FP32.
The old RGB tail remains in the coefficient feature path; its free RGB value
does not enter output directly. Flag defaults off; incompatible packed/ADC paths
reject. Optional initialization permits only the two new coefficient tensors.

This independently implemented discrete single-frame head is motivated by
sample-weight reconstruction in the [2026 ACKN primary paper](https://people.csail.mit.edu/cjbisc/burst/burst_paper.pdf).
It uses no ACKN code/weights, continuous MLP or burst pipeline. Our DC observation
is an inference from its normalization equation, not a claim about the authors'
trained color quality.
Noisy weights can correlate with noise and combined filter gain is not limited
to one, so clean-constant preservation is not noisy-field unbiasedness or a fix.

Targeted CPU suite: 43 passed, 1 skip. Full CPU suite: 528 passed, 9 CUDA-related
skips. The first full run exposed one new FP32 reference-average test error;
corrected to FP64 with unchanged bounds and production code unchanged. Across
100 random arithmetic cases, maximum error against FP64 is 1.49e-7 for the
implementation versus 1.73e-6 for direct FP32 pooling. Retained the original log.

Genuine V60 full4k EMA initialization loads every existing tensor exactly, leaves
actual DINO frozen, and introduces only weight+bias for the new head. The initial
output is exactly bilinear, not parent-quality-preserving. Actual frozen legacy
versus candidate/default-off predictions match bitwise for two native256 photos
and one 126×158 odd variant. Four actual CPU/B1/native64 updates match 2+2 restart
in all nine whole-state fields, numeric logs and input hashes across Commons,
native and paired domains. All 93 model/93 EMA tensors and 91 AdamW states are
finite. New source bundle:
`411d1669b050b8074d7a9d030b3c42ef1af6764c6f20efbd08ecf5466dc632d8`.

Saved experimental EMA independently matches reconstructed tensors, including
DINO, and two natural-photo predictions exactly. Across 64 clean constant cases
(four colors, four CFAs, two conditioning profiles, two CPU precision modes),
maximum RGB error is 5.96e-8. These are clean fields, not noisy restoration-quality
tests. No new GPU work. [Documentation](../docs/raw-kernel-reconstruction.md) and
[results](../docs/results/raw-kernel-CPU-preflight.json) hold source, inputs,
states and logs. Future CUDA memory/gradient/portability and trained detail,
color, false-texture and real-photo evidence are still required. Starting output
changes, so future comparisons must account for new-head initialization/warmup.

Queued an independent full 4×/8× area audit behind actual producer 1953180's exit:
owner 2032560/creation 1792209281.47, frozen driver
`f784f9255a743400ae242bc8fd62c041f95fe4ad13e08f476541b963dc1a4431`.
Its archived executed source has the original import ordering; a separate private
copy's Ruff-only import cleanup was not applied to the live frozen operator.
It will stop for actual 48-thumbnail review; no model manifest substitution.

Queued primary quality panels after both long-data arms freeze at 4000: owner
2036802/creation 1792209597.41, driver
`c980cf341454e33a83ad171cd3d0c004302e687bf46c90c436173ad3852fa44d`.
Uses immutable model/panel source, counts two CNNs plus three classical methods
and 448×(2 CNNs + Malvar) = 1344 analytic rows. No GPU inference until exact
trainer-owner exit. Independent statistics, hue, state and native review remain
required afterward. Keep working V43/README, original schedules/data and the
protected-final boundary.
