# Coupled Poisson counterfactual data primitive; no quality claim

Recorded: 2026-11-07T02:22:11-08:00 (America/Los_Angeles).

While the original V159 training job continues unchanged, I prepared a separate
training-data primitive for matched present/empty targets. Existing crossed-line
data already supports matched target geometry. The new sampler decomposes each
Poisson rate into a common minimum and independent positive increments, then
shares Gaussian read noise. Each marginal retains the existing sensor model;
the pair is deliberately dependent. This is not a pair of independent captures.

For nonnegative sensor levels and positive shot above the inherited numerical
floor,pre-ADC covariance is shot*min(a,b)+read and difference variance is
shot*abs(b-a). A future paired-response loss could exploit lower variation in
the difference while every model forward still sees one noisy image. It might
also amplify noise sensitivity; no quality outcome follows from the coupling.

16 CPU tests pass in1.02s. Independent analytic moments and low-count Poisson
PMFs pass,alongside ADC/overexposure,empty-mask exact equality,broadcast,RNG and
early-rejection checks. A separate audit freezes source/test/old sensor text
and retains four262,144-sample pairs with actual noisy/pre-ADC arrays. Analytic/
observed difference variances are8e-8/7.995328e-8 atISO100,
5.12e-6/5.118787e-6 atISO6400,and1.024e-5/1.023545e-5 atISO12800;ADC-only zero.
There are12 Poisson/four Gaussian sampler calls excluding tests,and no neural
calls,training,source lookups or RAW decodes. New arrays are local hot-cache
fixtures of synthetic constants;original media and dataz remain untouched.

This sampler is not integrated into V159 or any trained model. A future trial
must compare ordinary versus paired-response losses on the same paired data,
keep real test captures/siblings out of training,and score actual quiet/coarse/
weak errors together. V159's recipe,owners and queued review stay fixed.

[Construction and scope](../docs/coupled-counterfactual-noise.md) ·
[Frozen audit and fixtures](../docs/results/coupled-counterfactual-noise-v1.json).
