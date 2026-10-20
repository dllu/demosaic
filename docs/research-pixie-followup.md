# Recent semantic-routing follow-up

[PixIE, Lin et al., July31 2026 v3](https://arxiv.org/html/2605.23531v3)
separates initial denoising from foundation-guided pixel refinement and keeps
semantically modulated features out of cross-scale denoising propagation.
It studies low-light RGB enhancement, not Bayer RAW. The inspected primary
paper and [author publication page](https://lrr-rachel.github.io/) do not link
a released code/weight artifact. This is an availability observation on
October20, not proof that no implementation exists elsewhere.

Our inference from the current code: the ConvNeXt feature pyramid already
bilinearly upsamples projected fields, so spatial continuity alone is not a
missing feature. Semantic routing differs: our projected offsets enter the
restoration encoder and propagate onward. That is a distinct future hypothesis,
with no demonstrated RAW benefit. The paper is not a reproduced comparator,
and no publisher code, weights or data have been incorporated.

Before changing architecture, the [new noise-proxy diagnostic](stabilized-noise-proxy.md)
checks a concrete upstream assumption. Its generated-field results find an
average dark-level variance close to the unit proxy, substantial correlation,
and deviations with both signs across regimes. They do not justify a blanket
noise-scale adjustment or identify the cause of missing detail. This narrows
the next action without changing current conditioning or mixing interventions
into the live spectral experiment.

A future routing study would need to isolate how DINO enters the predictor,
hold data/physical conditioning fixed, and include a matched control. It must
preserve a verifiable common initialization or explicitly compare fresh models;
moving nonzero learned offsets is not function-preserving. No new training
recipe is launched from this literature note. Complete the original spectral
budgets and native/numerical review before choosing another quality experiment.

Those original budgets and the subsequent photo/component diagnoses are now
complete. The independent [V90/V91 late RGB study](late-dino-rgb-v90-v91.md)
retains the mature model's existing early DINO guidance and compares spatial
versus globally pooled late prompts in the same zero-output RGB head. It reuses
one frozen encoder pass. [Genuine CPU/CUDA engineering and process-boundary
restart checks](late-rgb-engineering.md) pass; original4000 quality budgets are
launched. This is a controlled new hypothesis, without reproduced PixIE scores
or a demonstrated Bayer benefit yet.
