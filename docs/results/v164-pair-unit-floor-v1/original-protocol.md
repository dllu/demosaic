# Weak-pair training units: V164

V164 tests stronger supervision of weak paired differences while retaining
V163's flat-target anchor, architecture and cached observations. CUDA parity
and sixteen numerical leaf-output checks pass. Restored smoke has 94 finite
Adam states; the first forty control steps and both unit traces pass. Original
1,000-step training is underway. Quality and native comparisons remain pending. The measured
[V163 quiet-bias gain](harmonic-phase-inputs.md),
[V162 grain reduction](flat-target-anchor.md) and
[V161 stronger mesh response](harmonic-frequency-context.md) remain available.

The existing pair loss compares restored present/background differences with
their exact constructed target difference. Sensor simulation shares Poisson
counts and read draws within each pair, so read noise cancels before ADC.
The modeled shot-increment variance is `shot * abs(clean_a - clean_b)`.
Its image/phase mean supplies a training unit, previously floored at 16 DN16.
This unit is a pre-ADC proxy, not restored-RGB covariance or confidence.

The [complete cached-unit audit](results/v164-pair-unit-floor-inputs-v1.json)
reconstructs all **1,382** original FP32 units bit-exact from retained unfloored
mean variances. Of 1,240 supervised pairs, **620** hit the old floor. This
includes **455/614 mesh pairs**, whose median unfloored RMS is 8.60 DN16.
The corresponding counts are 73/428 photographic and 92/198 weak-texture pairs.
The additional 142 ADC-only pairs keep zero total supervised loss.

The candidate lowers only this floor to **2 DN16**, leaving pair-loss weight 1,
dimensionless Charbonnier epsilon 0.003, flat-target weight 0.25 and all other
losses fixed. Unit ratios stay within 1–8; unaffected pairs keep identical units.
For floor-limited pairs, large-error gradients can increase up to eightfold
and very small-error gradients up to sixty-fourfold. The physical Charbonnier
transition also changes with the unit. This is relative weighting and a change
of physical transition scale, rather than a uniform multiplier on every pair.

The loss still includes unchanged target regions, so differential false detail
there is penalized more strongly too. Errors common to both pair members remain
invisible to the pair term; ordinary RGB, local/regional error and flat-target
supervision remain necessary. No pair label, target, unit or reference enters
inference. The smaller floor provides no flat-field safety guarantee.

An [optimizer-state audit and source review](results/v164-objective-motivation-v1.json)
also rejected reducing Adam epsilon as the next primary intervention: its
median denominator contribution is only about 0.1% in the actual final phase
and support weights. Tiny prefix gradients alone did not establish starvation.
The previously catalogued structural-guidance paper was revisited; its mosaic
head accompanies a different DINO/SwinIR system, and our parent already has an
auxiliary mosaic head. Its Gaussian/decoded-sRGB/fixed-RGGB results do not
establish our RAW fidelity. No external code, weights or reported gains are
adopted by this trial.

Both fresh heads have **124,909 parameters / 47 tensors**. All **89 neural
source modules are unchanged**. The same 1,000 V160 batches of four retain exact
source, noise, parent and target bindings. Only candidate training units change;
the original cached arrays remain immutable. LR, AdamW, clipping and EMA clocks
stay fixed. The control must reproduce V163's complete 1,000-row trace and final
raw/EMA/Adam states, plus 1,644 actual outputs before archive storage adoption.
Final validation requires 94 finite Adam states and four strict CPU endpoint
loads. Both heads keep 900 supervised and 100 zero-gradient ADC updates.

All **199 CPU checks pass**, including 19 new independent FP32 unit-rounding,
loss and full-output-adjoint tests. Checks cover unit-ratio bounds, zero/empty
cases, detached targets, invalid variances, gradient scaling, unchanged-target
false detail, common-error blindness and zero ADC weighting. CUDA parity replays
28 archived contexts at all four CFAs and native 256/384/512/768 sizes: 56 root
calls. Ten inherited flat-mask/loss checks and six new paired-unit/loss/adjoint
backwards use leaf outputs, adding no neural forwards.

The fixed quality review covers 822 cases at both raw/EMA endpoints of both
heads: 3,288 main calls, 1,644 exact control replays and 1,644 new external
arrays. No additional neural ablation is planned. Including discarded/restored
smoke and training, the plan is **5,364 root calls / 11,424 head images**;
sixteen leaf-output CUDA backwards and CPU tests are separate.

The native review retains 72 images / 24 noisy–denoised–exact-GT triplets,
with eight comparator columns: V156 raw; V157/V158/V159 EMA; V160 ordinary and
paired EMA; V161 EMA; and V162 EMA. Planned independent rendering checks cover
61,824,000 RGB channels. All methods share source ROIs and display transforms;
160×160 crop pixels are never resized. Both standing GFX scenes include sky,
building, foliage, coarse fence, both fine-cab priors/windows and native camera
JPEGs. Independent ISO100 captures differ in aperture, shutter and motion:
qualitative references, not exact GT. Protected captures, JPEGs, siblings and
18 held-out Commons sources remain excluded from training.

The study launches once with a 12 GiB CUDA quota, RAM floors of 52/32 GiB and
new local/external reserves of 56/144 GiB plus a 0.5 GiB projection margin.
Remaining local artifacts are bounded to 0.25 GiB; predictions stay external.
Older evidence is retained. Resource guard errors now include the observed
free-space values. Exact PID/create-time identities are monitored until
terminal; observation timeouts do not authorize restarting workers.
No new parent/DINO/source/noise/RAW/original or `/mnt/dataz` access is required.

[Actual readiness evidence](results/v164-pair-unit-floor-preparation-v1.json) ·
[Prospective LA diary](../diary/2026-11-07-07-45-23-v164-pair-unit-floor.md) ·
[Recipe](../configs/quality-v143-pair-unit-floor-v164.yaml) ·
[Unit helper](../scripts/pair_unit_floor.py) ·
[Tests](../tests/test_pair_unit_floor.py).
