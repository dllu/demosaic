# Frequency gating needs delivered-output checks

Recorded: 2026-11-07T08:59:07-08:00 (America/Los_Angeles).

Read the method, data, experiments, ablations and limitations of the October
[RIECR preprint](https://arxiv.org/html/2610.28191v1). Its exposure-restoration
benchmark differs from joint camera-RGB demosaicing. No paper code, weights or
data are adopted, and the running V165 recipe stays unchanged.

An independent deterministic numerical fixture checks a tempting inference
about frequency separation. A 3×3 kernel with center1 and eight neighbors−1/8
has exactly zero DC, yet maps identity input covariance to output variance9/8.
It annihilates a constant field but can amplify noisy-flat variance. No random
noise or sensor draw is needed: the exact64×64 circular operator gives the
covariance analytically.

A fixed nonnegative half-image gate applied after this high-pass response
turns a zero-mean period8 signal response into mean0.027459. A separately
constructed correction can have zero whole-image mean while shifting the
left quiet half by1 and the right half by−1. These are own scalar algebra
counterexamples, not paper kernels, trained outputs, Bayer experiments or
performance measurements.

This matters because our current spectral proposal is restricted in frequency
before spatial support is applied. That ordering does not preserve a zero
correction mean after gating, and whole-image mean conservation alone cannot
protect local quiet fields. The next architecture decision should check
post-support camera RGB, including local bias and noise, rather than assume
that a zero-DC/high-pass construction solves flat artifacts. V165 remains the
current matched test; its trained quality is still pending.

[Cached-source identity, exact fixtures and executable source](../docs/results/frequency-gating-reading-20261107-v1.json).
The prior [released nonlocal-model comparison](../docs/nonlocal-matchfilter-cpu-probe.md)
already evaluates that separate April2026 approach; no duplicate neural run
was launched during this reading.
