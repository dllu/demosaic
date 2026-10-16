# Noise-aware packed detail experiment

The first packed architecture leaves substantial grain because its identity
detail bypass retains58.03% of MHC Gaussian-noise power even with a clean coarse
prediction. This variant filters that detail in physical coordinates before
combining it with the coarse CNN prediction and learned native phase output.
It is experimental; quality is not established by the engineering tests.

`model.packed_detail_prior: true` requires stabilized packed RGB processing.
The default is false, preserving the existing full-resolution and V38 paths.
Let `d` be normalized MHC RGB minus bilinear expansion of its area2 mean, and
`v` the marginal noise variance of that difference. The initial detail estimate
uses local signal power `s = max(mean7(d²) - mean7(v), 0)` and Wiener gain
`s / (s + v)`. At zero variance, gain is exactly one. The final native output
keeps the existing coarse correction and learned twelve-channel phase head,
and replaces the identity detail by this filtered detail.

Noise energy is derived from144 independent basis impulses through the actual
MHC/area2/bilinear operators. The central2×2 output has complete support in a
12×12 sensor field. The squared coefficient sums retain each of the four input
phases, allowing input/output WB ratios for Gaussian profiles. Poisson/GAT
profiles use unitWB in stabilized coordinates. These are interior marginal
variances; RGB covariance is not whitened, low-count GAT variance is approximate
and tile boundaries are approximate. No reference or fitted transform is used.

All normalization, filtering, native projection/skip and expectation inverse
retain IEEE FP32 math. Deep CNN/DINO keep the existing BF16 training/FP16
inference policy. Nonpersistent energy buffers are3D to support channels-last.
The four separate CFA measurements and color labels remain available to the
trainable trunk/head. No crop/output pixels are resized for reporting.

`phase_lr_multiplier` optionally gives the new phase adapter/head a larger LR
while the pretrained trunk and DINO adapter retain the base schedule. Default1
keeps the old single optimizer group. Other positive finite values create
separate groups; warmup/cosine scheduling preserves the multiplier. Resume
rejects a changed multiplier or changed model configuration.

[Engineering smoke/resume receipt](results/packed-detail-smoke-v1.json): eight
actual CUDA updates across Commons/native/paired domains, genuine pinned DINO,
finite losses/gradients and nonzero updates in both phase modules. Resume from
step6 to8 keeps a10× LR ratio; an attempted change to1 is rejected without
changing the checkpoint. These steps are not quality or throughput evidence.

All321 tests pass. Added checks compare default packed output bit-for-bit with
a SHA-pinned V38 implementation, validate every CFA's color/phase variance by
Monte Carlo with actual WB, preserve16-bit ADC ramps under BF16 and odd packed
dimensions, attenuate flat Gaussian detail noise, verify gradients/checkpoint
roundtrip in channels-last, and check optimizer grouping/scheduling/resume.

The planned matched trial is [V40](../configs/dino-anchored-packed-detail-b16-v40.yaml)
versus [V41](../configs/dino-anchored-packed-detail-fast-phase-b16-v41.yaml):
phase multipliers1/10, same V34 EMA, seed47, batch16, baseLR3e-5/planned3000,
original53 native4 captures/31 scenes and fixed Commons4/paired data. Both stop
after1000 updates and must match all41 V38 observation hashes before review.
The V39 six-source extension is deliberately separate. Known/unseen real,
full427 and full102MP GFX evaluations remain required; frozen comparators may
be reused only with matching data/metric protocol and classical parity checks.
