# Preserve mature RGB and launch directional/interval training

Implemented a zero-initialized opt-in RAW residual around the mature native RGB
prediction, avoiding the old RAW-kernel experiment's bilinear output reset. Five
measurement-derived candidates use unfiltered and horizontal/vertical/diagonal
33-sample phase averages. Existing RGB/DINO features and a small packed local
innovation/noise/CFA network choose signed residual mixtures. A separate ADC-white
gated correction supplies censored-channel freedom. The branch adds25,800
parameters/eight tensors and preserves the parent's common initialization/RNG
and exact initial FP32/BF16 output/gradients.

Added the independently motivated pre-clipping reference-white interval loss as
an opt-in nonnegative weight, restricted to sensor-valid camera supervision.
Reference white/black constrain feasible intervals; interior reference channels
retain exact linear-sRGB supervision. Weight zero preserves the existing loss
and gradients. Paired losses and all inference/display/export transforms stay
unchanged. Added20x scheduled LR grouping for the new branch, checkpoint
initialization support and explicit resume recipe guards.

Meaningful tests cover independent FP64 filter samples, signed constants,
coherent-carrier/noise behavior, zero heads/RNG, actual gradients and learning,
CFA censorship, portable checkpoint behavior, common parent gradients, optimizer
coverage/LRs, mixed-domain interval routing and exact restart. Full CPU suite:
1,059passed/9skipped in104.36s, followed by four additional constant-scene cases
in the30-passing focused suite. Existing22 source-sensitivity tests also pass.
Ruff and whitespace checks pass. These fixtures establish engineering behavior,
not trained restoration quality.
Two additional genuine-checkpoint resume checks reject changed interval weight
or branch LR multiplier with the intended errors and unchanged checkpoint SHA256,
without initializing CUDA.

Genuine original20k V63 EMA CPU preflight: four B1/native64/FP32 mixed-domain
updates per arm and an independent2+2 restart. Model/EMA/AdamW/RNG/best/step match
exactly after interruption, with identical observations across arms. Genuine
CUDA preflight: six B16/native256/BF16 updates per arm, workers4+2+2,97 finite
gradients in all12 checks,99/99/97 finite model/EMA/AdamW states, exact initial
parent output and unchanged frozen official DINO. Peak CUDA allocations9.257/
8.162 decimal GB are execution observations, not a stable arm comparison.

Frozen and launched **new** V78/V79 original4k study from fresh genuine V63 EMA,
not from the closed V77 checkpoint. Both use the new branch, sensor-valid camera
supervision, seed51/B16/native256/BF16, commonLR1e-5/headLR20x/warm100, same
cleaned84,867 Commons/native128/paired32 manifests and the requested4x→geometry/
PSF→area2 selected-domain path. Only interval weight differs:0/.1. The complete
4,000 updates per arm are fixed in advance (64k example draws each); intermediate
checkpoints do not trigger quality-based extensions. V76/V77 and earlier failed
studies remain closed. V43 remains the working reference and README pixels stay.

Training plan SHA256:
`85ca5b72a717cd73b7a14d93004a72247b19165c9a7968162919028a192033b8`.
Frozen217 files. Controller404904/1792353195.14; first child404910/1792353195.81.
Root `.cache/experiments/directional-interval-v78-v79-original4k-v1`.
Independent review queue SHA256:
`124eac6a7bb3e1cc78d053f131fc72d5e7c6ec508ae1b1443679880e488f17f2`;
controller405679/1792353257.72. Separate217-file frozen checkout with identical
package bytes, final4k lineage checking and fresh V63 parent primary inference.
Review starts only after successful exact owner/child exit; manual statistical
and native-pixel closure remains necessary. Resource caps:24GiB CUDA,40GiB
launch RAM headroom,128GiB root/500GiB external reserve,10,800s per arm.

See [fixed study and quality criteria](../docs/directional-interval-v78-v79.md),
[engineering report](../docs/directional-interval-engineering.md) and
[public receipts](../docs/results/directional-interval-engineering-and-launch-v1.json).
The new full quality results, native GT triplets/GFX review, any eligible fresh
full-frame16-bit output and cold/warm timing remain outstanding. No SOTA,
decisive real-photo superiority or100MP/10s claim.
