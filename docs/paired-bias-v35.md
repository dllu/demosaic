# V35 center-crop gain diagnostic

Input-only multiplicative correction does not improve V35's mean center-crop
scores. Keep inference unchanged. This uses 18 preselected 512px development center
tiles, one per noisy capture across nine scenes, **not the full paired suite**.
It must not be compared numerically with the 72/90-crop development means.
[Complete diagnostic and source/weight identities](results/paired-bias-v35-1k.json).

| Variant | Measured-CFA PSNR | Auxiliary AHD RGB PSNR | SSIM |
| --- | ---: | ---: | ---: |
| V35 unchanged | 50.19500 | 36.35851 | .904204 |
| V35 global gain | 50.15958 | 36.35793 | .904241 |
| V35 channel gains | 50.06492 | 35.94631 | .903566 |
| RawNIND global CFA-LS | 49.50755 | 35.63716 | .889985 |
| RawNIND channel CFA-LS | 49.50266 | 35.71197 | .890386 |

Gains fit predicted measured phases to the noisy observations with valid input
values in [0,.98). They never access references. This fit is not an unbiased
clean-signal estimator: denoised outputs and noisy inputs can remain correlated.
Some low-signal blue-channel estimates are large (up to 1.50), and their use
reduces scores. An oracle reference-derived correction is not tested or used.

For each case/channel, mean error and mean squared error use registered measured
reference samples, excluding 32px borders. The median ratio
`sum(channel_bias**2) / sum(channel_mse)` is 2.81%, with a 47.94% maximum. It is
an equal-channel DC fraction, not a spatially independent noise-power estimate.
Most cases' error is not explained by a constant per-channel offset. Registration,
remaining reference noise and optical differences are still part of this
development diagnostic; AHD RGB is **not exact RGB GT**.

`scripts/diagnose_paired_bias.py` now supplies each case's explicit shot/read
profile to stabilized models; the old variance-map-only invocation could not
run that model family. It records conditioning, immutable checkpoint path/hash
and its own source hash, includes both RawNIND calibrations and refuses to
overwrite a completed result. V35 step 1000 SHA256:
`09a491b65e618e5b33819717f57bf54f8b7dd520ce3108b8c888caeb71d65741`.
Its [review includes exact synthetic GT and accurately labeled real native crops](expanded-v35-1k-review.md).
This diagnostic introduces no trained model, inference default or performance
claim on protected-final/GFX reference targets.
