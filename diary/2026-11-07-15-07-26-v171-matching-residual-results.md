# V171 matching residual improves standalone flats but worsens quiet color

Recorded: 2026-11-07T15:07:26-08:00 (America/Los_Angeles).


The fresh 2.09M matching residual trained on all1,000 existing V168 rows:
900 optimizer updates/3,600 images and100 ADC-only skips. V169 EMA and cached
V143/DINO parents remained frozen. Step8 model/Adam/EMA/RNG restoration is exact;
continuation starts at9 with no repeated prefix. All141 trainable tensors receive
nonzero gradients during training;all141 final Adam states are finite. The
upstream CUDA sampler input-gradient is atomic and not bit-exact deterministic.
All114 relevant CPU tests pass.

The useful result is standalone-flat fidelity. Against V169 EMA,new EMA full
native512 RMS falls1.205/1.521% at ISO6400/12800;coarse32 falls1.730/1.735%.
All48 inputs improve in both measures. Mesh response rises1.257%,to3.88482% of
constructed amplitude,present RMS falls0.519% and absent RMS falls1.089%.
The raw endpoint has a similar smaller mesh gain and all48 coarse improvements.
These are measured gains worth retaining,with substantial costs below.

EMA quiet RMS rises30.729/25.775%,to5.289473/7.979617 DN16. Quiet DC color error
rises91.043/93.219%,despite0.287/0.610% lower spatial error. Raw casts are worse.
All60 native figures were actually viewed in15 original-detail sheets. Amplified
quiet fields beside step/bar/striped detail show stronger purple/blue casts and
remaining blotches. Normal-display edges look close to V169. Fine cab crossings
remain missing under both priors;synthetic weak mesh and natural microtexture
remain heavily smoothed. Ordinary main sky is smooth;building/foliage/coarse
fence show no decisive gain. ADC planes,bark and fur remain exactly V169;the
zero-variance bypass avoids V170's periodic artifact without learning new ADC
restoration.

All1,644 frozen V169 evaluations replay their existing fingerprints exactly.
Quality has1,644 composed calls,1,500 new matching calls and7,500 nested sampling
calls;144 ADC outputs bypass the new branch. Independent audit checks all6,576
actual input fingerprints and durable rows. Posthoc metrics/addition cover only
36 selected native cases:72 RGB+72 residual arrays,430,196,736 bytes,582 scalar
checks. Other new outputs are streamed/fingerprinted and independently
norm/decomposition/addition checked in process,not retained as a full archive.
Independent Decimal arithmetic checks645 means. All1,000 training bindings,
900 weighted totals and900 inherited clean-mask fingerprints pass.

The first quality initializer stopped on missing `train_v43_quality_trial`,
imported by a metric helper,before model/journal creation. Its terminal owner,
claim,source and traceback are preserved. A separate prepared receipt binds the
unmodified dependency and successful CPU-only metric construction. Corrected
owner67581/create1794092243.59 uses the original frozen runner and plan;no
completed scientific inference repeats. The current preparer adds the missing
helper;AST checks prove its training/review/runtime functions unchanged.

Actual new matching work totals2,406 CUDA calls/5,115 images plus3 CPU admission
calls. Frozen-component CUDA totals2,548 calls/5,257 images;these are nested
components,not new DINO parents. Admission includes3 discarded synthetic updates
and8 sampler-only fixtures,with both original admission failures preserved.
The successful training/review owners,zero-forward failed initializer andthree
admission owners are terminal. No original/dataz reads,source/noise draws or new
parent/DINO calls occurred.

Retain V171 as a full/coarse-flat option,V169 for quiet color,V161/V164 for
stronger learned response,V165 for grain and the earlier useful strengths.
V120 remains the broad recommendation. The failure suggests examining the new
correction's color means and its image-wide noise scaling,especially beside
bright structure;this is a hypothesis to test,not an established cause. Fine
crossings without invented flat-field structure remain unresolved.

[Report and all native comparisons](../docs/learned-matching-residual.md) ·
[Final evidence](../docs/results/v171-matching-residual-final-v1.json) ·
[Publication checks](../docs/results/v171-matching-residual-publication-verification-v1.json).

A posthoc diagnosis uses only the already saved native residual arrays,with no
new neural calls. On four saved RGGB quiet contexts per prior,EMA quiet RMS is
5.217/7.698 DN16 versus V169's4.210/6.526. Removing the new correction's global
RGB mean yields4.982/7.508;attenuating by local supplied noise RMS relative to
image-wide RMS yields4.598/7.093. The latter helps more but still loses to V169.
This does not establish a full-cohort gain or cause. It motivates testing local
noise normalization/output units and context-dependent color control, rather
than assuming a global DC subtraction solves the failure. No derived model or
new prediction archive is published by this diagnosis.
[Selected-array diagnostic and exact source](../docs/results/v171-selected-native-scaling-diagnostic-v1.json).
