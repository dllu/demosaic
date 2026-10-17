# Check noise-fit support without changing the model

Previous goal turn made progress: the fifth Commons snapshot launched with
10,368 images and genuine startup checks, plus a queued full-cache audit.
Current exact checks confirm V67 trainer/controller and the data producer/audit
waiter remain live. Training passes5,425; data preparation passes2,550 without
recorded failures. No restart or original model/source/data/schedule change.

Reviewed recent primary restoration work. RPG-VST(July2026) flags single-image
noise fitting as a practical failure source; our current estimator already
uses rejection/binned medians. Rechecked SG-for-JDD's stated public repository:
actual GitHub API returns404 at08:34UTC. Neither availability nor paper claims
substitute for an implemented quality result. No external code or weights added.

Executed a prespecified240-case CPU estimator study: six knownPG profiles,
five field/texture/clipping/span conditions and eight local draws. Native1024,
ADC16/black.03, original32px/max4096/seed42 estimator. Fixed variance probes
.001/.005/.02/.08/.2/.6 and1dB flag declared before execution. No restoration,
real RAW decoding, target fitting, camera calibration or production change.

All192 non-narrow fits are accepted; all48 narrow-gray fits reject. None exceed
1dB at tested levels inside accepted bin means(max.440495dB), but55 exceed1dB
somewhere in the full probe; every such case's largest error is at.001. Worst
7.042466dB occurs outside accepted means[.033643,.793760], with in-range max.110946.
This exposes extrapolation limits of the flag, without proving wrong GFX noise.
Independent verification hashes280 saved arrays and recomputes1,632 scalar
fields using Torch64/Python math; max difference8.74e-14. Plot/CSV exported and
the actual plot viewed. Moment-mask docstring clarified after execution; AST
matches executed calculations except that docstring. No numerical changes.

Described the retained standing GFX support using only four saved noisy contexts:
accepted bin means[.007338,.085891]; below-range disjoint phase-patch means
sky0/building6/foliage104/fence30 of256 each, above-range0/8/0/0. Independent
math.fsum exactly reproduces1,024 means/counts. These noisy means and different
sampling do not certify calibration or assign the synthetic error rate to GFX.
Noise coefficients/reference/model outputs and active benchmark remain unchanged.

Keep the estimator and current conditioning fixed. Investigate conditioning
sensitivity or measured calibration separately if final real quality remains
poor. This diagnostic is no restoration improvement, new training budget,
protected-final score, promotion or completed SOTA claim. All three new scripts
pass Ruff; source/model modules are unchanged.

[Study and reproduction](../docs/noise-calibration-fit-support.md).
[Independent/source/support receipts](../docs/results/noise-calibration-synthetic-stress.json).
