# Multiscale correction with measured-CFA innovation

This experiment addresses the fine-detail loss and coarse color variation in
[the current GFX texture crops](gfx-qualitative.md). It is a hypothesis under
training, not an established quality improvement. V16 remains the reviewed
model until real RAW, synthetic and native-crop comparisons justify a change.

V24/V25 append the same 255,840-parameter correction network to frozen V16
step5000. A two-level encoder/decoder uses existing gated blocks, skip paths
and channels 24/48/96. It sees the current RGB estimate's local high-pass signal
in noise units, log noise-scale maps, actual CFA phase labels and projected
frozen decoder features. The output is an additive RGB correction scaled by an
input-derived noise proxy. The final head starts at zero, and zero sensor
variance forces zero correction even after training. The scale is a proxy,
not a claim about posterior RGB noise covariance.

V25 also sees four channels of **measured-CFA innovation**:

`(original packed RAW − current RGB sampled at the CFA phases) / noise scale`.

This may expose structure removed by earlier denoising and distinguish a noisy
current estimate from the original measurements. That benefit is an inference
to test, not a result. V24 supplies zeros to these four channels, keeping the
same capacity, RNG consumption and initial weights. Neither receives reference
pixels, target-derived gains or quality scores as inference inputs. The features
are clipped in noise units; physical RAW values and RGB predictions are retained.

The existing Bayer/DINO/fine-refinement path remains frozen, so the experiment
can first test whether measurement access helps without also changing the
previous restoration model. This adds inference cost; it is a quality experiment,
not a claim to have reached the 10-second target. A successful correction would
still need a quality/speed consolidation review.

Both arms use seed 45, LR 5e-4, the existing 50/50 paired-RAW/Commons recipe and
original losses, with a planned 5000-step schedule and a predeclared first
review at 1000 steps. Only the new branch trains. Per-step data RNG isolates
observations from optimization, and sampled batch hashes check that both arms
actually see the same input/target draws. The previous native-target substitution
is disabled for this comparison. Protected final and GFX qualitative scenes and
siblings remain excluded from training.

Physical feature construction, noise normalization and output scaling remain
IEEE FP32. The correction's neural operations also default to IEEE FP32, with
the previously validated optional inference precision selector available for
later measurement. Base training uses BF16; reviewed inference uses explicit
FP16 base compute and default FP32 refinement.

Validation before training: 182 tests passed, including phase-aware access to
measurements, removal of that access in the control, arbitrary even geometry,
zero-variance identity, frozen-weight preservation, exact CPU checkpoint resume,
resume mode rejection and CUDA FP16 convolutions with FP32 physical output.
Both genuine-DINO trial models were compared against frozen V16 on four CFA
layouts and ADC/noisy inputs: 6,291,456 RGB values per arm were bit-identical.
[Source hashes, initialization and startup receipt](results/pyramid-v24-v25-startup.json).

Configs: `configs/dino-pyramid-control-v24.yaml` and
`configs/dino-pyramid-raw-v25.yaml`. Run directories:
`/mnt/external/demosaic/runs/dino-pyramid-{control-v24,raw-v25}/`.
Each run archives actual source, manifests, weights and initialization hash.
Quality reports after training must contain at least two native noisy/denoised/
reference triplets per candidate; this startup note makes no performance claim.

Research context: the [AIM 2025 RAW denoising challenge](https://arxiv.org/abs/2510.06601)
emphasizes synthetic training and evaluation across multiple camera models.
Its abstract supports keeping camera generalization explicit; it does not prove
this innovation representation or reproduce any participant's results. The
implementation here reuses this repository's independently written blocks.
