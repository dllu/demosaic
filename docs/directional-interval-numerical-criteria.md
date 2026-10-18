# Fixed numerical checks for the directional study

The [V78/V79 protocol](directional-interval-v78-v79.md) fixed these criteria
before training. A separate checker now applies them to the final primary
statistics without rounding. It does not change the experiment or decide
whether its images are acceptable.
[Tests, historical replay and frozen command](results/directional-interval-numerical-checker-v1.json).

| Comparison | Required mean effect | Required confidence bound |
| --- | ---: | --- |
| Each arm vs fresh V63: known-four measured CFA PSNR | ≥ +0.05 dB | Lower 95% scene bound > 0 |
| Each arm vs fresh V63: unseen-five measured CFA PSNR | ≥ +0.05 dB | Lower 95% scene bound > 0 |
| Each arm vs fresh V63: full427 rendered PSNR | ≥ +0.05 dB | Lower 95% source bound > 0 |
| Each arm vs fresh V63: full427 rendered SSIM | ≥ −0.0001 | No additional bound in the fixed protocol |
| Matched V79 vs V78: full427 rendered PSNR | No separate minimum | Lower 95% source bound > 0 |
| Matched V79 vs V78: known/unseen measured CFA PSNR | Each ≥ −0.03 dB | No additional bound in the fixed protocol |

An effect equal to its stated minimum passes that mean check. A zero lower
confidence bound fails the strict positive-bound check. The matched interval
effect is recorded separately from either arm's comparison with its parent.
Unfavorable canonical camera-linear results remain in the output with their
target-convention caveat; they are not replaced or omitted.

The checker requires the complete six-method audit counts, the correct
source/scene counts, one comparison per required metric and matching checkpoint
identities. Parent/control comparisons must use the same fresh report and case
files as the candidate. It checks linked file hashes once per distinct path,
rejects nonfinite or reversed confidence intervals and preserves the original
comparison rows. The CLI requires verified final 4,000-step boundaries and
rejects historical preflight results as evidence for the new models.

All 17 focused tests pass. They cover exact thresholds, gains that would round
up to the minimum, zero confidence bounds, SSIM and matched-loss limits,
incomplete coverage, duplicate/missing comparisons, wrong references,
checkpoint mismatches and invalid numbers. A separate historical V76/V77/V63
replay parses all 15 required comparison rows unchanged. The frozen CLI was
also tried against the actual incomplete live review: it refused to produce an
output because both final boundaries are not yet available. No new V78/V79
quality result was generated.

This tool applies thresholds to the separately audited primary statistics. It
does not recompute predictions, metrics or bootstrap intervals, and those
intervals do not measure uncertainty across training seeds. Native color,
detail, highlight and artifact review remains required even if every numerical
check passes. Its output always disallows automatic extension or promotion.
Any eligible candidate still needs the separate full-frame FP32, 16-bit export,
native-pixel and timing checks described in the protocol.

V78's retained step 2,000 checkpoint is independently audited: all 99 model,
99 EMA and 97 AdamW states are finite, and every new branch parameter retains
nonzero optimizer moments. SHA256:
`3205312b282152e56727e3a8300190a6a9038cd623bf8ca77be2597ecfdfc714`.
This is an execution milestone on the original schedule, not a quality gate.
Both final4k runs and the [complete review](directional-interval-original4k-review.md)
have now finished. The original checker rejects both arms' camera criteria and
the matched interval photo-benefit criterion. Full81-triplet/125-cell review
also retains texture/highlight limitations. No extension/promotion; V43 stays
the working reference.
