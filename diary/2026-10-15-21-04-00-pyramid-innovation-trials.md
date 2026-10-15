# Multiscale measured-CFA correction trials

Previous turn made progress: new GFX pair/crops, optional FP16 refinement and
completed native body/control review committed/pushed. Full goal remains open:
V16 still trails RawNIND on real development and does not reach10sec/100MP.

Implemented optional255,840-parameter pyramid correction with noise-unit RGB,
variance/CFA/context features and direct packed RAW minus CFA-sampled prediction
innovation. Two-level gated encoder/decoder is identity-initialized and exactly
zero atzero sensor variance. Existing checkpoints disable the new branch.
Physical operations remain IEEEFP32; neural inference precision canbe selected.
Added mutually exclusive pyramid-only training and exactresume mode checking.

182tests pass in12.44s, Ruff passes. Tests verify measured-CFA access acrossfour
patterns and its removal in thecontrol, arbitrary even geometry, warmstart,
frozenweights, zerovariance, CUDAhalf/FP32physical outputs and exactCPUresume.
ActualDINO/V16 startupcheck covered6,291,456 RGBvalues perarm: both are bitwise
identical toparent acrossfourCFAs×ADC/noisy. Initialweights match betweenarms.

Started V24control (innovationzeroed) andV25 (innovationenabled), same255840
parameters, seed45, LR5e-4, original50/50 paired/Commonsloss/data, perstepRNG,
sampledactualbatchhashes. Planned5000schedule, stopfirst1000 forreview. Existing
body/DINO/finebranch frozen. No native-targetsubstitution or protectedfinal/GFX
scenes. Startup sampledhashes match. Ownjobs session6699/71267; logs
`.cache/train-pyramid-{control-v24,raw-v25}-1k.log`; sourcearchived perrun.
Observedstep50 finitegradients/loss, ~.5sec/step perarm underconcurrency,
~1.81GB CUDApeak each, ~70GiB available. Donot restart onobservation timeout.

Hypothesis: direct measurement access pluslarger context may restore detail
removedby preceding interpolation/denoising and suppress coarseresiduals. This
is not proven bystartupchecks. No promotion or performanceclaim. Reviewboth
realpanels, matchedsyntheticscreen and>=2nativecroptriplets per candidate.
Configs and methodlimitations: `docs/pyramid-refinement.md`. Newly inspected
AIM2025 abstract is researchcontext forcamera-general synthetictraining, not a
reproduced method or support forour untestedinnovation representation.
