# Current model choices

**V120 Small remains the general recommendation.** The competing-orientation
head improves one fixed mesh's weak sector but lowers aggregate mesh response.
The complementary stage retains a small lower-noise weak-increment gain with
mean strong response preserved. Shared-edge training has small quiet gains with lower response; analytic
edge refinement remains restricted synthetic evidence. [Architecture and commands](architecture.md).

| Choice | Useful strength | Remaining weakness |
| --- | --- | --- |
| [V120 Small](v120-v121-primary.md) | 37.04008 dB on 427 photos; known/unseen CFA means 54.31272/54.00872 dB; verified 102MP RGB16 exports | Fine foliage, mesh, neon and dark-field mottle |
| [V131 completed continuation](v131-broad-primary.md) |427-photo +0.04000 dB with400/427 source gains; targeted faint-ADC +0.14555 dB; modest high-noise carrier/flat gains | Unseen-camera −0.04381 dB; ADC color maximum1,816 DN16 versus55.5; high-noise weak-band error slightly worse; soft foliage/fine cab crossings; no new full-frame validation |
| [V131 ADC Malvar, opt-in](v131-adc-projection.md) | Fixed existing policy, identical91 weights; ADC photo+0.15074 dB versus V131,382/427 gains; ADC color maximum19.98 DN16 | Weakest ADC band error+1.43%, lower analytic carrier amplitude,45 non-improving photos; positive-noise V131/camera costs unchanged; no new full-frame validation |
| [V132 RAW attention, completed20k](v132-endpoint-quality.md) | Reproducible full-model ablation; ordinary-material +0.00046 dB versus V131; all20k input hashes match | Faint ADC −0.40978 dB versus V131/−0.26423 versus V120; shadow −0.00438 dB; missing cab crossings/soft foliage; no broad or100MP validation |
| [Local conditional waves, complete panel](local-wave-full-panel.md) |400/far weak response1.826%→2.690% above V143; lower global-support quiet/increment error in all six cells; fewer global cab ripples above V120 | Quiet/increment error still above parent; sources1/2 dominate gains; higher-noise weak structure and real crossings mostly missing; executed historical matcher |
| [Phase measurement aggregation, analytic pilot](phase-measurement-aggregation.md) | Same H1 discovery:current400/far weak response2.80%→12.68%, strong43.33%→65.96%; both projection arms reviewed | Quiet/increment error+5.44%/+1.94%, severe building bands, poor high-noise response; consistent nuisance projection does not repair real artifacts |
| [Fixed-proposal neural nuisance, full panel](neural-nuisance-full-panel.md) | All8 sources/CFAs/repeats: quieter than conditional analytic in all6 cells;400/far quiet/increment−0.485%/−0.362%; smaller building bands | Weak response2.476%→2.299%, parent1.826%; quiet/increment still+0.058%/+0.055% over parent; source1 dominates gain; missing fine crossings |
| [Native512 nuisance/complete-edge ablations](neural-nuisance-context512.md) | Complete edge-offset search fixes far-background coverage; withheld noisy sensor RMS substantially lower; zero new neural calls | Weak response near-parent0.957–0.959% versus preferred256's2.690%; high-noise/cab detail missing; geometry fix alone does not improve reconstruction |
| [Hann512 analytic discovery](neural-nuisance-hann512.md) |400/far weak response0.958%→2.702%, weak-increment RMS−0.093% versus parent in both pilot sources; quiet+0.0037%; matched neural arm has smaller building correction | Weaker strong response/higher full RGB error than256 neural; most weak structure and real crossings absent; two-source development scope, high-noise gains negligible |
| [Local129 amplitudes](spatial-carrier-amplitudes.md) | Same Hann geometry:400/far analytic weak2.702%→6.241%, strong37.587%→52.053%; lower increment/full error | Severe green/magenta building bands,306.78 DN16 added correction;1600/far weak response falls; fine cab crossings absent; explicit two-source ablation |
| [Global background/local129, full panel](global-background-full-panel.md) | Versus256 NN,400/far weak2.299%→2.778%, strong37.032%→48.055%; all8 sources improve strong response/full RGB error; much smaller added real cab ripples | Quiet/increment+0.126%/+0.169% versus parent; mean increment worse than256 in all6 cells; source1 largest response gain, weak crossings/high-noise detail unresolved |
| [Fixed-background phase reconstruction](global-background-phase-reconstruction.md) | Neural400/far weak27.390%, strong75.116%, lower full RGB error; both sources gain response | Quiet/increment+2.352%/+0.434% versus parent; building75.18 DN16, fine crossings missing; two reused sources |
| [Neural-guided phase, analytic nuisance](neural-guided-phase-pooling.md) |400/far weak28.702%, increment−0.946% versus parent with both sources improving; lower quiet/increment error than unguided phase; building531.58→130.59 DN16 | Quiet+0.541% versus parent; residual bands, high-noise weak detail/fine cab crossings absent; neural-nuisance arm increment regresses; needs A-only neural guide fields, two-source scope |
| [Neural residual-reselection ablation](neural-nuisance-reconstruction.md) |400/far quiet RMS−0.493%; no added building correction because arm returns V120 exactly | Weak response3.686%→0.900%, increment error+0.028%; fine cab crossings missing;88 masked background calls, no broad quality/speed claim |
| [Harmonic analytic ablation](local-wave-shapes.md) | Same pilot H1→H3 far weak response 2.80%→5.46%, strong 43.33%→46.88%; small full-error reduction | Quiet/increment error +0.993%/+0.745% versus H1; new building color bands, missing real crossings; H1 remains default |
| [Individual harmonic support](individual-wave-validation.md) | Far quiet/increment RMS 4.06592/11.89181→4.05049/11.85942 DN16 versus H3 group; weak response 4.07% | Near quiet error rises; building bands persist; expanded affine background further raises quiet error; explicit ablations |
| [V114 Tiny](v114-v115-quality.md) | Lower tested ADC maximum: 51.73 versus V120's 55.52 DN16 | Different photo/camera tradeoffs |
| [V187 pooled waves](pooled-phase-wave-comparison.md) | Quieter wave option; 5.359% constructed-GT mesh amplitude | Incomplete crossings, false waves and small flat/absent costs |
| [V195 response pressure](directional-response-comparison.md) | 5.575% GT mesh response; stronger than V187 in that comparison | Quiet RMS +0.334–0.376%; fine crossings unresolved |
| [V198 CFA innovation](cfa-innovation-wave-comparison.md) | 11.158% GT mesh amplitude; stronger colored synthetic and real cab modulation | New green/magenta building fringes; quiet RMS +1.151–1.648% versus V195 |
| [V200 cross-scale support](scale-supported-cfa-wave-comparison.md) | Quiet RMS −0.059–0.119% and fresh-flat RMS −0.022–0.030% versus V198 | Mesh response falls to 11.102% GT; building fringes, ripples and incomplete crossings persist |
| [Shared-edge training](shared-edge-comparison.md) | EMA quiet RMS −0.051–0.076% and cached fresh-flat RMS −0.036–0.045% versus V200 | Mesh response falls to 10.874%; present-mesh error rises; fringes/ripples/incomplete crossings persist |
| [Complementary stage](complementary-edge-response.md) |400/far weak response8.14%→9.43% with mean strong response retained and slightly lower quiet error | Extra capacity/training; high-noise quiet/flat costs, little fixed-mesh change, real fringes/incomplete crossings persist |
| [Competing orientations](competing-orientation-comparison.md) | Mesh2302 weak sector 28.41%→33.55%; fresh far-edge weak increment 3.13%→5.06% at1600 prior with lower quiet error | Strong response falls; other fixed weak sector worsens; mean mesh response 10.607%; fringes/false waves persist |

V198/V200 do not combine strong fine-detail recovery with clean quiet fields.
These are bounded experiment results, not a broad ranking against V120. Mesh
response percentages describe projected amplitude, not overall restoration
accuracy. Real ISO100 captures differ in aperture, exposure and motion and are
qualitative references, not exact GT.

Earlier useful strengths remain available: [V171 standalone flats](learned-matching-residual.md),
[V172 balanced matching](local-noise-matching.md), [V173 quiet fields](weak-gradient-matching.md),
[V181 spatial loss](flat-spatial-evidence-comparison.md), [V183 coherent pairs](coherent-pair-evidence-comparison.md),
[V185 smaller support](spatial-context-wave-comparison.md), and
[the optional supported-amplitude stage](supported-wave-amplitude.md).
Their measured gains and weaknesses remain documented; the historical catalogue
is [preserved in full](history/current-model-through-v200.md).

## Loading and inference

The normal full-frame command remains in the [README](../README.md).
`demosaic-experiment models` lists the explicit preset catalogue.
`demosaic.models.registry.load_model("v120")` verifies the declared checkpoint
identity. V187/V195/V198/V200 use composed component loaders with explicit
historical checkpoint translation. They require supplied base RGB plus physical
RAW inputs; their component exports alone are not full-frame parent models.
[Package interfaces and limits](architecture.md).

`load_model("v131", checkpoint=...)` exposes the completed full-model continuation
with its declared checkpoint hash. It trains the original restoration trunk on
the revised cohort for 20k additional updates; it does not add the RAW-attention
branch. The matched V132 arm has completed20k; its
[endpoint review](v132-endpoint-quality.md) finds a0.410 dB faint regression
against V131 and near-tied ordinary detail. The earlier1k advantage did not
persist. `load_model("v132")` verifies the portable114-tensor EMA export.
[Completed-control gains and counterexamples](v131-endpoint-quality.md).
The [completed broad review](v131-broad-primary.md) supports V131 as an
experimental photo/faint-detail option with camera and ADC-color costs. A
fixed existing ADC projection repairs the color panel and improves ADC photo
PSNR, with weaker-band error and carrier-amplitude costs. The
[`v131-adc-malvar` export/preset](v131-adc-projection.md) makes that operating
point available. V120 remains the general recommendation.

## Current research and evidence

The [A-only neural background diagnostic](withheld-neural-background.md) predicts
withheld building/cab sensor samples better than the analytic H1 fit. It uses
four fresh frozen-model/DINO calls, with held-out values removed before inference.
Its [matched whole-context nuisance correction](neural-nuisance-reconstruction.md)
now has complete numerical/native review: it reduces some added errors but
loses clearest-prior weak recovery. This remains an experimental guard/control,
with no general model promotion. Its [fixed-proposal follow-up](neural-nuisance-fixed-proposals.md)
recovers part of the weak response and reduces quiet/increment error versus
analytic H1. That is the preferred nuisance variant for further weak-detail
work; both measured operating points and their real-photo limitations remain.
Its [native512 ablations](neural-nuisance-context512.md) fit the far edge better
but lose the weak-response gain. The
[completed full source/CFA/noise review](neural-nuisance-full-panel.md)
confirms lower added errors versus analytic H1, with remaining costs versus
parent and source-dependent response.
The [Hann512 follow-up](neural-nuisance-hann512.md) adds an analytic option with
lower low-prior weak-increment error than256 neural, at weaker strong response
and higher total RGB error. This useful operating point is available without
changing the256 default or claiming general quality superiority.
The [local-amplitude ablation](spatial-carrier-amplitudes.md) adds synthetic
response/error gains but severe real building bands. Its opt-in implementation
and exact standalone conditional API remain available; global amplitudes stay
the default.
Keeping the [neural background global](global-background-local-carriers.md)
reduces the local-fit building bands, at a weak-response cost. This stronger
detail option remains opt-in while its [full comparison](global-background-full-panel.md)
runs; source1 dependence and real fine-crossing loss remain explicit.

The [shared-edge cache](paired-training-coverage.md) is completed and audited:
156 changed rows and 844 exact adoptions. Its [matched training and complete
raw/EMA review](shared-edge-comparison.md) measure a quieter, weaker-response
operating point. The [configured runner](experiments.md) retains the same V200
architecture/loss recipe and all experiment evidence. The separate
[analytic edge-refinement comparison](withheld-cfa-edge-refinement.md) improves
restricted synthetic weak-direction/false-error tradeoffs; it is not a neural
camera recommendation.

The [fresh independent-noise finite-wire test](near-edge-response.md) measures
roughly 1% weaker-increment response near a strong edge and 1.5% far from it in
the nominal noisy condition, with no clear gain from shared-edge training.
The [completed lower-noise extension](edge-snr-ladder.md) reaches strong/weak
responses of 86.7%/8.1% far from the edge at the clearest prior. Shared-edge
training supplies no clear weaker-direction gain across the three profiles.

The [competing-orientation prototype](competing-wave-candidates.md) divides the
same eight carrier slots between two angular families. Its proposal diagnostic
reaches more weaker fundamentals but loses some strong-family coverage. Matched
900-update training and the [full two-endpoint native review](competing-orientation-comparison.md)
are complete. One fixed mesh has a real directional gain, with weaker aggregate
mesh response and persistent artifacts. The [complete three-noise review](competing-edge-response.md)
finds higher far-edge weak response with strong-family losses: slightly lower
quiet error at1600, slightly higher at400. Every full-image RMS mean increases.
These specific strengths do not establish broad weak-detail recovery.

The [complementary stage](complementary-cfa-branch.md) has completed training above the
complete frozen V200 EMA path. It adds a fresh 643-parameter head and up to eight
nonduplicate proposals, with unchanged training observations/objective/schedule.
The [complete standard/native review](complementary-comparison.md) finds almost
unchanged weaker sectors, tiny aggregate mesh gains and slightly higher
quiet/flat error. The [completed three-noise review](complementary-edge-response.md)
retains a small conditional lower-noise gain, with far-edge weak response
8.14%→9.43% at400, mean strong response retained and slightly lower quiet error.
The `complementary` preset exposes its trained component. Exact frozen-baseline
checks pass at both endpoints. A sealed
evaluator-only repair handles legacy receipt metadata without changing training
or numerical model code.

The [seven-state native viewer](images/v200-scale-supported-cfa-wave-v1/native-viewer.html)
retains raw/EMA endpoints, both protected GFX scenes, independent ISO100
references, noisy/restored/exact constructed-GT triplets and failure cases.
V200's complete endpoint/audit/native/export evidence remains in its report.
Broad state-of-the-art quality and 100MP within 10 seconds remain goals.
