**A quarter support floor recovers some mesh response, with higher quiet-region error.**
Compared with exact V166 routed-common controls, V167 raises mean constructed
mesh response **47.33% raw / 47.55% EMA**, reaching **3.239% / 3.248% of GT
amplitude**. Present-image RMS falls **1.153% / 1.094%**. This is useful measured
response recovery from the almost closed V166 path. V161's 4.83–5.24% and V164's
4.30–4.43% remain stronger learned responses. Real fine cab crossings are still
incomplete. Quiet RMS rises **2.84–3.74%**, spatial error rises **2.26–2.60%** on
all32 quiet inputs, and standalone full-flat means rise **0.189–0.382%** versus
V166. The requested fine-detail recovery with reliable flat fields remains open.

The only intervention is the shifted quarter-floor support mapping at identical
124,909-parameter heads, initial weights, cache, losses, common backward routing
and optimizer. A positive floor prevents support from approaching zero but does
not force the frequency proposal to recover signal. All256 present-mesh mean
supports lie within1e-4 of the floor at both candidate endpoints. Their
pre-support coefficient RMS falls from control8.4502e-5/8.4363e-5 to
5.8498e-5/5.9512e-5; direct RGB correction RMS is0.3620/0.3160 DN16 versus
0.3335/0.3162. These archived scalar observations describe adaptation, not an
isolated explanation of the quality change. Full support maps were not retained.
[Recorded bounds, activity and ADC identity checks](results/v167-archived-support-summary-v1.json).

Mesh present RMS is8.981523/8.994781 DN16. Actual blank-region RMS rises
0.793%/0.953% and wholly absent-image RMS rises0.686%/0.836% versus control.
Absent-image means are0.050%/0.411% above V143. An additional diagnostic, frozen
after launch but before V167 scores or completed review existed, groups every
recipe by zero/one/two nominal periods<=10 native pixels. There are26/29/9
distinct recipes, with related CFA/noise variants rather than independent scene
replications. For the nine both-fine recipes, response changes from
-0.000810/-0.000762 to0.011309/0.011392; present RMS falls from
10.208917/10.217452 to10.075513/10.087129 DN16. Blank error rises there too.
This remains only about1.13% of constructed GT amplitude. Nominal periods do not
measure post-geometry spectral peaks.
[Additional declaration](results/v167-mesh-period-strata-preparation-v1.json) ·
[All period strata and per-recipe means](results/v167-mesh-period-strata-v1.json).

Native512 full-flat RMS means are18.481399/23.981424 raw and
18.505695/24.031410 EMA for ISO6400/12800. Against control,42/48 raw and41/48 EMA
inputs worsen, with maximum increases0.237933/0.312141 DN16. Coarse32 means
improve0.135–0.153% raw and0.0137–0.0238% EMA;47/48 raw and28/48 EMA inputs
improve, with individual maximum costs0.006020/0.011248 DN16. All48 coarse errors
remain below V143; full-flat means remain0.168–0.376% below V143 even though
12 raw and25 EMA individual full errors exceed it. Coarse and total flat error
therefore give different conclusions.

Quiet RMS is4.221290/6.728466 raw and4.141840/6.547331 EMA,6.23–9.36% above
V143. Against V166,25/32 raw and29/32 EMA quiet total errors worsen, with
maximum increases0.851428/0.452393 DN16. All32 spatial errors worsen at both
endpoints; their maximum increases are0.220952/0.220428 DN16. Quiet DC bias rises
4.61–6.56% versus V166 and14.29–30.86% versus V143. Whole mixed-image means
remain below V143, which does not establish accurate quiet neighbors. The
original-pixel decomposition separately checks spatial error and DC bias.

Natural-photo full-RMS means improve in two of four cohorts and worsen in two,
at each endpoint: changes range-0.0203% to+0.0253% versus control. All four
cohort band-response means decline at both endpoints. Retained-photo band
errors improve slightly, while organic-photo band errors worsen. ADC-only photo
full RMS improves0.0164% raw/0.0104% EMA versus control; all eight outputs now
differ from V143. Their mean displacement is only0.04479/0.04298 DN16 RMS,
with maximum absolute differences2.29489/2.26754 DN16. This is displacement,
not target error. All192 reviewed constant-field endpoint outputs stay exactly
at V143. ADC slope full error rises0.0700–0.0717% versus control while coarse
error falls0.184–0.186%.
[Post-hoc ADC displacement size audit](results/v167-adc-photo-displacement-v1.json).

All72 native figures, including24 noisy/restored/exact-GT triplets, were
actually viewed in18 original-detail sheets. The two fixed procedural mesh
crops still lose a crossing family or nearly all faint wires; periodic detail
recovers more lattice with directional/support defects. The protected GFX cab
windows under both priors retain weak incomplete diagonal strands; changes are
subtle and do not establish new complete crossings. Main-scene coarse fence
and building geometry survive, foliage stays soft, and sky looks smooth at+2EV.
The ISO100 AHD/JPEG views differ in aperture, shutter, movement and processing;
they are qualitative references, not GT. Amplified standalone and quiet crops
show broad color mottle and added fine texture. Smooth unamplified contexts do
not override those measured quiet costs. Natural bird, butterfly, bark and
vegetation retain substantial fine-texture softness.

Retain the bounded variant as an implementation that restores some delivered
response and modest coarse-flat improvement relative to V166. Preserve V166's
quiet-color strength, V165's grain/total-flat strength, V161/V164 stronger detail,
V158 quiet accuracy and V157 coarse correction. V120 remains the broad model
recommendation. The [training-coverage audit](results/mesh-training-coverage-20261107-v1.json)
finds only13/614 noisy training pairs with both carriers in the real reference's
dominant7.12–9.40 pixel interval and median actual signal RMS2.48 DN16. This
supports testing better fine-family coverage across a contrast/noise ladder
with matched empty scenes; simply reducing already weak contrast is not an
established solution. It does not establish a cause of these model tradeoffs.
