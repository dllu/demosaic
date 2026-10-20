# V92: preserve the mature path while learning late RGB refinement

The completed [component diagnosis](late-rgb-component-review.md) locates most
of V90/V91's low-contrast ADC response loss before the new head. This motivates
a new training-scope test. It does not establish that freezing improves quality
or identify which training gradients caused the earlier adaptation.

V92 initializes the same zero-output **global** head from the genuine V63
original20k EMA. Only the head's24 tensors /100,547 parameters train. All91
common restoration tensors and the frozen DINO remain exactly at their parent
values. EMA averages only the24 head parameters, leaving common EMA tensors
untouched. With measurement inputs detached as in production, the common
forward constructs no backward graph. Global gradient clipping consequently
operates on head gradients alone; that follows from the training-scope change.

Architecture, initialization, native256/B16, seed55, the reviewed88,508 Commons
sources, native128/106 groups, paired32, sensor-valid Charbonnier losses,
4×→geometry/PSF→area2, physical noise, deterministic BF16/channels-last and the
original4000-step schedule remain V90's recipe. The head retains20× the base
LR1e-5,100 warmup steps and a10% cosine floor. Each complete run sees64,000
examples. The empty1× base optimizer group retains the original schedule
layout, while only the24 head parameters acquire AdamW state.

The completed V90 global original4000 endpoint is a **fixed historical
exploratory reference**. V92 was chosen after its outcomes and the component
diagnosis; this is not a new independently randomized two-arm confirmation.
Do not rerun or extend V90. Verify original observations/forward/loss
fingerprints at steps1–16 and every25, original LRs and final Python/CPU/CUDA
RNG. Compare all47 executed model modules: only training implementation may
differ; inference modules must remain byte-identical. V63 remains the fresh
parent comparison. Neither the rejected spatial head nor frozen pooling is a
deployment recommendation.

Before a full run, require the new scope/EMA/gradient/restart unit tests and
discarded genuine-weight CPU/B1/native64/FP32 and CUDA/B16/native256/BF16
mixed-domain16-update preflights. Each must compare uninterrupted16 against
8+8 in genuinely different processes, including model, EMA,24 AdamW states,
best, Python/CPU/CUDA RNG and observations. At every saved boundary, require
all91 common model **and EMA** tensors byte-identical to V63. Check first actual
forward against head-bypassed parent replay, initial model/DINO hashes, finite
head gradients, absence of common backward inputs/gradients and nonzero learned
head output/modulations. Resume must reject a changed training scope. These
checks are engineering evidence, not quality training or speed measurements.

Freeze sources/configs/inputs before running. Reuse the established48GiB
launch/24GiB active RAM floors, root64GiB/external500GiB disk reserves and24GiB
CUDA quota. Require60s of launch headroom; bound resource waiting and each full
arm to14,400s and each preflight subprocess to3,600s. Stop only exact owned
workers, preserve failures, and do not retry, change the schedule, extend or
promote automatically. GFX3879/3880 and all siblings remain excluded from
training; originals remain read-only and cached qualitative tests remain fixed.

After the original4000 endpoint, require unchanged FP32 known4/unseen5/full427
photos,16 procedural sources, all seven conditions/four CFAs,418/416-source
sensitivities, canonical camera-linear scores, all analytic/ADC/hue/highlight
groups and standing GFX crops. Keep every unfavorable case. Require actual
native viewing before numerical decisions, with at least two small identical
native noisy/restored/GT triplets and all source/ROI/hash/noise/exposure
metadata. The independent ISO100 GFX rendering is a qualitative reference.

Candidate eligibility still requires at least+.05dB over V63 on photo, known4
and unseen5 with positive95% lower source-bootstrap bounds, photo SSIM loss
at most.0001 and no new visible failure. Report matched V92−V90 effects and
their intervals, without treating the historical comparison as independent
training-repeat evidence. A weak-detail benefit additionally needs+.05 signed
gain on both existing highest-noise carriers, flat spatial-luma RMS at most
1.25×V90, and no individual ADC gain loss greater than.05 across all192 original
slots. Retain all12 ADC means and distinguish repeated deterministic ADC draw
labels from independent observations. No quality gain, SOTA, decisive real-photo
superiority or100MP/10s result is assumed.
