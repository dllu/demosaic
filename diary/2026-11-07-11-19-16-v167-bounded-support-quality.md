# V167 bounded support recovers response with quiet costs

Recorded: 2026-11-07T11:19:16-08:00 (America/Los_Angeles).

Completed the original V167 run with no scientific failure or restart. The
[final report](../docs/bounded-spectral-support.md) preserves every endpoint,
all 822 cases, all 72 native figures/24 triplets and both standing GFX scenes.
The [final evidence](../docs/results/v167-bounded-support-final-v1.json) copies
32 exact receipts; preparation preserves 16 earlier receipts and 56 source
texts. All 89 prior neural files remain unchanged, with one isolated bounded
support module added. Main checkpoint SHA256:
`57bc0b5b01188f39b5763cc3953538f0021efa692bb16850d9ac286af2abf822`.
Candidate raw/EMA export hashes:
`db7a078ba2b4aaca4156663f4f986e21085614322476988eba60ae57f393ed71` /
`3ab3975e79386e4f50f71d18af21cafbe9444c48020e040d3dfe87e9ac11c509`.

Only support mapping differs: the candidate has a shifted quarter-floor sigmoid,
with the same initial support .5 as control. Heads retain 124909 parameters/47
tensors, V166 losses/common backward routing, original data and initialization.
Every one of 1000 control trace rows, final raw/EMA/Adam state and 1644 actual
control predictions reproduces V166 exactly. All 266 CPU checks, 56 GPU
compatibility roots, 24 CUDA leaf checks, restored 8+2 smoke and 94 final Adam
states pass. Independent FP32 reconstruction matches all 2000 weighted losses;
1000 independent pair-unit records/2000 fingerprints and inherited mask checks
pass. The metric audit passes 40210 scalars and 476 Decimal reductions, maximum
difference 4.55e-13. All 10 original scientific owners are terminal: 5364 roots /
11424 head images, no new source/sensor/parent/DINO/RAW/dataz calls. All 3288
original review support bounds pass. The final publication verifier is recorded
separately and must pass before committing this quality report.

Response rises 47.33/47.55% raw/EMA versus V166, to .0323874/.0324840 of exact
constructed GT amplitude, and present-image RMS falls 1.153/1.094%. This is a
useful recovery from the nearly closed path, below V161/V164 response. All 256
candidate mesh means remain within1e-4 of the .25 floor; pre-support coefficient
RMS declines about30%. This adaptation does not isolate a causal explanation.
Empty-image error rises .686/.836% versus V166. Full-flat means rise .189–.382%,
while coarse means improve .0137–.153%. All48 coarse errors beat V143, but only
36 raw/23 EMA full-flat inputs do. Quiet means rise 2.84–3.74% versus V166 and
6.23–9.36% versus V143; all32 spatial errors worsen at both endpoints. Quiet DC
bias rises 4.61–6.56% versus V166. Mean whole-image improvements do not remove
these flat-neighbor costs.

An [additional period-strata diagnostic](../docs/results/v167-mesh-period-strata-v1.json)
was frozen after launch but before V167 scores or completed review existed.
All64 recipes are retained:26/29/9 have zero/one/two nominal periods<=10 pixels.
Both-fine mean response rises from slightly negative to about1.13% of GT;
present error falls, blank error rises. Nominal periods are not measured
post-geometry peaks; related CFA/noise variants are not independent scenes.
The [post-hoc ADC displacement audit](../docs/results/v167-adc-photo-displacement-v1.json)
follows the changed ADC photo identity: all eight candidate photo outputs differ
from V143, mean displacement only .04479/.04298 DN16 RMS, maximum2.29489/2.26754.
Their mean target RMS improves .0164/.0104% versus control; displacement and
error remain distinct. Constant-field outputs stay exactly at V143.

Actually viewed all18 original-detail sheets, recorded only after viewing. The
two synthetic crops still lose crossing families or nearly all faint wires.
Real fine cab changes are subtle, with incomplete crossings under both priors
and windows. Main coarse fence/buildings survive; foliage and organic detail
remain soft. Sky is visually smooth at+2EV, while40x quiet crops reveal broad
color mottle and added fine texture. ISO100 AHD/JPEGs remain qualitative, notGT.
README keeps eight small native triplets: V161 stronger mesh, V167 recovered
response, V166 quiet color and V165 total-flat/grain. Its old periodic-detail
triplet remains in the original report, now linked from README to keep the
representative set small; no original artifact was removed.

Retain bounded support as a useful implementation and response gain, with the
quiet cost explicit. Broad recommendation remains V120; V161/V164 detail,
V166 quiet color, V165 grain/flat, V158 quiet accuracy and V157 coarse strengths
remain visible. The earlier training audit motivates better joint fine-family
coverage across an explicit contrast/noise ladder with empty controls, not
simply weaker contrast. The user's combined fine-detail/flat-field objective
is still unresolved; completing this trial does not complete that goal.

