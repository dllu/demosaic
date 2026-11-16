# Current model choices

**V120 Small remains the general recommendation.** The competing-orientation
head improves one fixed mesh's weak sector but lowers aggregate mesh response.
The complementary stage retains a small lower-noise weak-increment gain with
mean strong response preserved. Shared-edge training has small quiet gains with lower response; analytic
edge refinement remains restricted synthetic evidence. [Architecture and commands](architecture.md).

| Choice | Useful strength | Remaining weakness |
| --- | --- | --- |
| [V120 Small](v120-v121-primary.md) | 37.04008 dB on 427 photos; known/unseen CFA means 54.31272/54.00872 dB; verified 102MP RGB16 exports | Fine foliage, mesh, neon and dark-field mottle |
| [V131 completed continuation](v131-endpoint-quality.md) | Four-source targeted faint-ADC +0.14555 dB; fur/wood weak-stratum error falls; ordinary/shadow +0.01539/+0.01673 dB | Bark faint regression; soft foliage/fine cab crossings persist; broad photo/camera/flat/full-frame quality unmeasured |
| [V132 RAW attention,1k progress](v132-progress1000-quality.md) | Matched faint-ADC +0.03356 dB versus V1311k; all four weakest-stratum RMS means improve | Faint mean remains0.23979 dB below V120; wood PSNR cost; no clear new cab crossings/foliage; production still training |
| [Local conditional waves, analytic pilot](local-validated-waves.md) | Two-geometry far weak response0.96%→2.80% above V143; lower quiet/increment costs than same-candidate global support; fewer global cab ripples above V120 | Source1 drives gain; quiet/increment error still above parent; most real mesh missing; full three-prior evaluation running |
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
branch. The matched V132 arm is training; its [early1k review](v132-progress1000-quality.md)
has a small faint gain against V1311k while remaining below V120.
[Completed-control gains and counterexamples](v131-endpoint-quality.md).

## Current research and evidence

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
