# Current model choices

The completed [V189 wider-separation trial](spaced-pooled-wave-comparison.md) regresses at the same 508-parameter / 900-update budget: mesh response falls **4.63% raw / 5.68% EMA** versus V187, and quiet spatial RMS rises **0.38–1.31%**, worsening 30/32 inputs in each state. Fresh-flat errors also rise slightly on 47/48 inputs. Small natural-response/DC gains do not produce clear new cab crossings. Keep V187 as the preferred experimental wave model. Both endpoints, audits, 60 viewed native figures / 12 triplets and two exports are complete. [Eighteen-state viewer](images/v189-spaced-pooled-v1/native-viewer.html) · [Exact evidence](results/v189-spaced-pooled-final-v1.json).

The [V190 native-alias diagnostic](native-wave-alias-geometry.md) finds 90.78% of exact mesh-template power in the strict principal square. Adding all four aliases around existing bins raises mean proximity only 0.445–0.674 percentage points; median principal proximity stays 3.348%. This gives little support to an alias-only fix as the next priority. Sparse local frequency measurements and the objective/readout deserve separate tests; geometric proximity is not a recovery bound or a quality gain. That diagnostic changed no neural code.

The completed [V191 dense local spectral readout](dense-local-spectrum-comparison.md) loses **14.31% raw / 16.54% EMA** mesh response versus V187, reaching **4.479% / 4.473% of GT** at the same 508-parameter / 900-update budget. EMA quiet spatial RMS improves **0.296–0.339%** on 26/32 cases and fresh-flat means improve slightly, but natural-detail response falls and real fine crossings remain incomplete. Keep V187 preferred; retain V191’s limited quiet/flat strengths as a tested dense implementation. Both endpoints, audits, all 60 viewed native figures / 12 triplets and two exports are complete. [Twenty-state viewer](images/v191-dense-spectrum-v1/native-viewer.html) · [Exact evidence](results/v191-dense-spectrum-final-v1.json).

The completed [V187 pooled-selection readout](pooled-phase-wave-comparison.md) is the current experimental wave option. At V185's same 508-parameter and 900-update budget, mesh response rises **5.23% raw / 3.64% EMA** to **5.227% / 5.359% of exact GT amplitude**; 168/256 present inputs improve in each state. EMA quiet spatial RMS falls **0.48–0.52%**, improving 27/32 cases. Absent RMS rises about 0.034% on all 256 inputs and fresh-flat RMS about 0.020–0.021% on all 48; false waves, mottle and missing real cab crossings remain. Both endpoints/all 822 cases, audits, 60 actually viewed native figures / 12 triplets and two strict exports are complete. [Sixteen-state native viewer](images/v187-pooled-wave-v1/native-viewer.html) · [Exact evidence](results/v187-pooled-wave-final-v1.json). V120 Small remains the general recommendation.

The completed [V185 smaller-support wave readout](spatial-context-wave-comparison.md)
is a retained smaller-support option. At matched 900-update head
training, mesh response rises **2.11% raw / 0.45% EMA versus V184** to
**4.968% / 5.171% of GT**, while quiet spatial RMS falls **0.42–0.55% raw /
0.83–1.38% EMA**. All 32 EMA quiet cases improve. Standalone flat RMS rises
0.001–0.003% and absent-mesh errors rise slightly; false striping, broad mottle
and real missing crossings remain. Quiet spatial RMS is still 0.34–0.96% above
frozen V183 EMA. Extra 192 parameters and smaller RAW contexts change together;
all 189 inherited tensors stay frozen. Both endpoints/all 822 cases, independent
audits, two strict exports and all 60 viewed native figures/12 triplets are complete.
[Fourteen-state viewer](images/v185-spatial-context-v1/native-viewer.html) ·
[Exact evidence](results/v185-spatial-context-final-v1.json).
V120 Small remains the general recommendation; earlier quieter/flat/detail options remain available.

The completed [V184 phase-aware readout](phase-wave-readout-comparison.md)
provides a stronger-response development option. Mean mesh response rises
**9.60% raw / 15.96% EMA versus frozen V183 EMA**, reaching **4.865% / 5.148%
of exact constructed GT amplitude**; 163/256 raw and 160/256 EMA inputs increase.
Quiet spatial RMS rises **0.936% / 0.765% raw and 2.346% / 1.807% EMA** at
ISO6400/12800. Quiet total RMS rises 0.836% / 0.575% raw and 1.855% / 1.386% EMA.
Raw has the smaller quiet cost. Constructed views show more periodic modulation,
but real cab crossings stay incomplete and quiet fields gain false fine striping.
Natural band-error means worsen in all four cohorts despite some response gains.

Only 316 new parameters train above the exact frozen V183 EMA component. Both
primary comparisons use that EMA initializer; added training, capacity and
freezing change together. EMA has 1.76% less mean mesh response than V161 EMA
with 9.18–10.70% lower quiet total RMS. Retain the direct readout for further
detail work beside V183's intermediate, V181's quieter and V172's balanced
comparisons, plus earlier flat/quiet/detail strengths. V120 Small remains the
general recommendation. Both endpoints/all 822 cases, full 900-total/five-checkpoint
and quality audits, two strict exports and all 60 actually viewed native figures/
12 triplets are complete. [Twelve-state viewer](images/v184-wave-readout-v1/native-viewer.html) ·
[Exact evidence](results/v184-wave-readout-final-v1.json).

The completed [V183 coherent-response comparison](coherent-pair-evidence-comparison.md)
adds an intermediate recipe on the same local-evidence architecture. EMA mesh
response rises **6.95% versus V181 to4.4390% of exact constructed GT amplitude**,
with237/256 inputs increasing. Quiet spatial RMS rises **0.668% / 0.386%**
at ISO6400/12800, worsening all32 inputs; quiet total rises0.538% / 0.357%.
Against V180, mesh response is2.406% lower and quiet spatial RMS0.492% / 0.089%
lower, while ISO12800 quiet total changes+0.0087%. Natural fine-band response
rises slightly versus V181, with mixed band-error changes. Full-flat RMS rises
0.013% / 0.022% versus V181. Both real cab windows remain soft/incomplete and
broad mottle persists. Retain V183's response recovery beside V180's stronger
response, V181's quieter output and V172's balanced comparison; none dominates
the combined goal. V120 Small remains the general recommendation. Both endpoints,
all822 cases, full900-total/five-checkpoint and quality audits, two strict exports
and60 actually inspected native figures/12 triplets are complete.
[Ten-state viewer](images/v183-coherent-pair-evidence-v1/native-viewer.html) ·
[Exact evidence](results/v183-coherent-pair-evidence-final-v1.json).

The completed [V181 spatial-loss comparison](flat-spatial-evidence-comparison.md)
adds a quieter option above the same local-evidence architecture. EMA quiet
spatial RMS falls **1.15% / 0.47% versus V180** for ISO6400/12800, improving
all 32 inputs; total quiet RMS falls 0.96% / 0.35%. Mesh response falls **8.75%
to 4.1504% of exact constructed GT amplitude**, still 5.78% above global V178
and 7.05% above V172. Only 90/256 mesh inputs increase against each earlier EMA.
Versus V172, EMA quiet total changes −0.214% / +0.109% and spatial −0.058% /
+0.283%, so it does not dominate the balanced comparison. Natural fine-band
response falls on all 128 inputs versus V180, coarse-flat means are mixed,
broad mottle persists and real cab crossings remain incomplete. Retain V181's
quieter recipe and V180's stronger response on the local architecture alongside
earlier strengths; V120 Small remains the general recommendation. Both endpoints,
all 822 cases, independent training/quality audits, two strict exports and
60 actually inspected native figures/12 triplets are complete.
[Loss-comparison viewer](images/v181-flat-spatial-evidence-v1/native-viewer.html) ·
[Exact evidence](results/v181-flat-spatial-evidence-final-v1.json).

The completed [V180 local phase-evidence comparison](local-phase-evidence-comparison.md)
provides a stronger matching detail option at the same parameter budget.
Raw/EMA mesh response reaches **4.5219% / 4.5484% of constructed GT amplitude**,
**15.23% / 15.93% above global V178**; 122/256 and 142/256 inputs increase.
EMA quiet spatial RMS rises **1.05% / 0.79%** for ISO6400/12800, worsening
31/32 inputs; quiet total rises 0.84% / 0.51%. Fine cab crossings still do not
clearly recover, and amplified quiet crops show stronger fine mottle over the
broad field. Native512 full-flat changes are mixed. Against V172 EMA, mesh
response rises 17.31% while quiet spatial error rises 1.11% / 0.76%.
Use the local-evidence architecture for further detail work while retaining
V172 as a balanced comparison, V173/V175 raw for quiet strengths, V171 for
flats and V161 for stronger learned response at a larger quiet cost. V120 Small
remains the general recommendation. Both endpoints/all 822 cases, full trace/
five checkpoints, independent audits and 60 actually viewed figures/12 triplets
are complete. [Native viewer](images/v180-local-phase-evidence-v1/native-viewer.html) ·
[Exact evidence](results/v180-local-phase-evidence-final-v1.json).

The completed [V178 measured phase-evidence trial](phase-evidence-comparison.md)
adds a small mesh-response option: **3.9243% raw / 3.9235% EMA of constructed
GT amplitude**, +0.920% / +0.915% over the same-endpoint matched control.
Only 121/256 raw and 125/256 EMA inputs increase. Quiet spatial RMS rises
0.011–0.052% versus control, and real fine cab crossings do not clearly recover.
Versus V172 EMA, evidence EMA has +1.196% mesh response and −0.052–0.089%
quiet total RMS, with ISO6400 quiet spatial RMS +0.052% and standalone-flat
RMS +0.116%. Retain the gain alongside V172's balanced, V173's quiet, V171's
flat, V161's stronger-detail and V175 raw's quiet strengths. V120 Small remains
the general recommendation. Both full training traces/ten checkpoints and
all four 822-case endpoints pass independent audits; all 72 native figures/
24 triplets were actually inspected. Broad mottle persists.
[Matched native-pixel viewer](images/v178-phase-evidence-v1/native-viewer.html) ·
[Final evidence](results/v178-phase-evidence-final-v1.json).

The completed [V175 fresh-noise continuation](fresh-noise-matching.md) reaches
9,000 total updates. Raw quiet RMS falls **0.14–0.27% versus V172**, with 21/32
inputs improving and 11 worsening; quiet spatial RMS falls 0.06–0.15% on 29/32.
Mesh response rises only **0.052% to 3.879% of exact GT amplitude**. ISO6400
native512 full-flat RMS rises 0.091%, photographic band response slips, and
fine cab crossings/broad mottle remain unresolved. EMA quiet ISO12800 RMS rises
0.213% despite lower spatial error. Keep raw's small quiet gain beside V172's
balanced matching baseline, V173 quiet, V171 flat and V161 detail strengths;
V120 Small remains the general recommendation. Both endpoints, all 822 cases,
60 actually viewed figures/12 triplets and final audits are complete, with all
141 Adam states at 9,000 and no successful prefix repeated.
[Native-pixel viewer](images/v175-fresh-noise-matching-v1/native-viewer.html) ·
[240 exact browser crops](results/v175-native-viewer-verification-v1.json).

The [completed V174 spread-sampling experiment](spread-sample-matching.md)
retains wide matching positions, but fine crossings remain missing. EMA quiet
total RMS falls **0.12–0.17% versus V172**, DC color error falls 0.36–0.43%, and
spatial RMS falls 0.04–0.08%. Mesh response slips **0.25% to 3.868% of GT**;
standalone-flat results are mixed and both coarse-flat means worsen. The native
changes are subtle. Keep V172 as the balanced matching baseline, V173 for its
stronger quiet/spatial gain, V171 for flats and V161 for learned detail. V120
Small remains the general recommendation. Both endpoints, 822 cases, 60 actually
viewed native figures, 12 triplets, 133 CPU tests and scoped audits are complete.
The [native-pixel viewer](images/v174-spread-matching-v1/native-viewer.html)
opens with V173 EMA versus V174 EMA; select V172 EMA for the main comparison.
All 240 browser crops match their source pixels exactly.

The [completed V173 gradient-loss experiment](weak-gradient-matching.md) lowers
EMA quiet spatial RMS **0.32–0.68% versus V172**, improving all 32 inputs. Quiet
total RMS falls 0.27–0.52%, and native512 total-flat means fall 0.25–0.30%.
**Mesh response falls 3.95% to 3.724% of GT**; natural fine-band response falls
2.63–2.88% on all 128 inputs. Broad mottle and real fine crossings remain
unresolved. Retain this modest quiet/spatial-error option alongside V172's
stronger response and V171's stronger flats. V172 remains the balanced matching
baseline for further detail work; V120 remains the general recommendation.
Both endpoints, 822 cases, 60 actual native figures, 12 triplets and scoped audits
are complete. All 162 focused checks pass (161 CPU tests and one CUDA stream
guard); no matching core or native sampler runs in that guard. An offline
[native-pixel viewer](images/v173-weak-gradient-matching-v1/native-viewer.html)
adds click/F-key flipping; all 240 browser crops match their PNG pixels exactly.

The [completed V172 local noise matching experiment](local-noise-matching.md)
reduces EMA quiet RMS **0.31–0.77%** and DC bias **1.33–2.55% versus V169**,
while mesh response rises **1.06% to3.877% of GT**. Quiet RMS falls21–24% versus
V171 and native crops show much less added purple/blue cast. Standalone-flat
full/coarse gains shrink to0.059–0.085%/0.021–0.050% versus V169; all48 inputs
worsen versus V171. Absent mesh RMS rises0.060% versus V169, broad mottle persists
and real fine crossings remain incomplete. Keep this local-unit variant beside
V171 flat,V161 detail and earlier quiet strengths; V120 remains the general choice.
Both endpoints/all822 cases/60 actual native figures complete;126 CPU checks,
900 updates,exact restoration,1644 V169 replays and144 ADC identities pass.
Independent posthoc metrics/addition cover36 selected cases,72 RGB+72 residuals.
An inherited output-label error is corrected by an audited derived view;original
records,arrays and frozen source remain unchanged,with no inference repeated.

The [completed V171 matching residual](learned-matching-residual.md) is a new
standalone-flat option above frozen V169 EMA and the cached DINO parent. EMA
full-flat RMS falls 1.21–1.52%, coarse RMS 1.73%, with all 48 native noisy inputs
improving versus V169. Mesh response rises 1.26% to 3.885% of GT, but quiet RMS
rises 26–31% and DC color error 91–93%; native quiet fields show stronger casts
and real fine crossings remain missing. Both endpoints/all 822cases/60 native
figures and audits complete. Keep this measured option beside the earlier
detail/quiet strengths; V120 remains the broad recommendation.

The [completed V170 released RAW matching comparison](nonlocal-raw-comparison.md)
adds a pinned April2026 nonlocal model and a DINO-parent RGB reconstruction.
Native 512 coarse-flat error falls 15.79–19.38% versus V169 EMA, but mesh response
falls to 2.406–2.533% of GT, quiet total/DC error rises and low-noise controls gain
periodic colored texture. Cab crossings remain missing. It uses external RAW
training data and is a comparison, not a replacement for V120 or the useful
V169/V161/V165 strengths. All 822 cases/60 native figures and scoped audits complete.

The new [supported-amplitude option](supported-wave-amplitude.md) keeps the
original positive global gate as selection and restores contrast only inside
unchanged reciprocal support. Fresh mesh response rises 26.4% and image RMS
falls 1.0% versus cross; mean/worst added blank RMS rise 42.1%/28.4%. All 256 absent
cases and 64 new photographic controls retain their parents. Full GFX mesh
contrast improves under both priors; nonperiodic texture, support seams, boundary
spill and highlight color remain unresolved. The explicit `detail` mode has
53 inspected native comparisons and complete RGB16 checks. V120 remains the general model recommendation. Detail is now the default
inside the explicitly enabled periodic stage.

The earlier [reciprocal green-support review](cross-phase-support.md) cuts fresh mean
added blank RMS 89% and its worst case 92% versus wide context, with 9.5% lower
response and 0.8% higher image RMS. Both full-frame mesh priors retain much of the
lattice. The known detached false patch is removed; weak/partial detail and
boundary spill remain. All 256 fresh absent neural cases retain parent values.
The explicit `cross` mode has 37 viewed native comparisons and complete RGB16
audits; it is a stricter support option, not a broad model-quality claim.

The [guarded wider-context option](wide-phase-context.md) uses actual 512-pixel RAW
contexts and measured higher harmonics on V143. Fresh 64-recipe response rises 14.4%
versus sparse support and image RMS falls 1.2%; mean added blank RMS rises 17.3%,
with a 17.4% lower worst case. All 256 absent neural cases and 5,120 ideal-flat
matched/mismatch executions retain parent values. The first unguarded version
failed the mismatch control and is archived. The explicit `wide` mode adds a
conservative variance floor; detached tail stripes, boundary leakage and very
weak recovery remain.

The [connected support/refit option](sparse-phase-support.md) gives stronger mesh
contrast on V143 and 12.8% higher fresh response with 34.0% lower mean blank spill
than refined TV. Worst-case blank RMS rises 39.2%; a known isolated stripe failure
is removed, while boundary leakage remains. Use the explicit `sparse` envelope;
Grid-TV is retained explicitly; Detail is the current optional-stage default. The wider sky, final absent inputs
and fixed photo/uniform checks retain parent values. Learned weights are unchanged.

The additional [continuous frequency option](offgrid-phase.md) gives modest,
placement-sensitive mesh changes on the same V143 parents. Fresh 64-recipe response rises 3.7% versus
fixed-bin TV with slightly lower texture error and 8.5% higher added blank RMS.
The tested wider sky and all 256 absent inputs stay unchanged; 4,096 new pure-flat
noise draws select no waves. Add `--phase-harmonic-refine-frequency` to the optional
TV stage; fixed-bin TV remains the default without that extra flag. Highlight
changes, partial spill, window sensitivity and runtime remain limitations.

The earlier [TV phase fit](edge-phase-envelope.md), available as explicit
`edge`, gives clearer crossing mesh on complete V143 frames and
unchanged wider sky. Fresh 64-recipe validation finds 48.8% less mean added blank
structure versus the Gaussian complex envelope, slightly higher texture error
and some blank regressions. Highlight color and runtime remain limitations.
Both `complex` and `scalar` remain available. General inference still disables
correction by default; weights are unchanged.

The earlier [scalar phase-aware correction](local-phase-harmonic-patch.md) on V1435k
patches gives stronger fine diagonals in both mesh windows/priors. In the active
new validation recipe, added structure in complete-patch blank regions falls62%
versus the first harmonic correction, with stronger response and lower error.
Spill remains measurable; tested96-photo/48-flat parent values are unchanged.
The [optional tiled inference path](phase-harmonic-inference.md) now processes
complete102MP RGB16 outputs. Regular window placement can weaken the centred-patch
gain, and CPU correction is slow. V120 stays the validated general recommendation.

The [completed V1435k review](v143-final5000-quality.md) gains0.26493dB faint
ADC PSNR and4.64% lower noisy-flat spatial RMS over V120 on fixed support.
Coarse noisy error remains2.63% higher and ADC-only spatial RMS12.85% higher;
training alone still lacks clear new mesh recovery. The read-only endpoint is
`/mnt/external/demosaic/models/v143-final5000.pt`. Its faint/shadow gains are
useful for further quality work. [Complete-frame GFX inference](phase-harmonic-inference.md)
now covers the main scene and both fine-mesh priors; full427/camera evaluation
remains open.

The [completed V1411k loss comparison](v141-gradient-epsilon-pilot.md) gains
.01528dB faint ADC PSNR over matched V129, with mixed weak-band changes and no
new fine-mesh recovery. Both continuations have about5.8% more coarse noisy-flat
error than V120, which remains the general choice. The completed
[V142 crossed-line/empty data trial](v142-crossed-line-pilot.md) adds.05212dB
faint ADC PSNR and4.55% lower noisy-flat spatial RMS versus V129. Coarse error
remains5.08% above V120, selected ADC-only DC bias worsens and mesh remains weak. The October V125/V131 workers and their dependents stopped;
the [V140 execution audit](v140-standalone-pilot.md) preserves their receipts.

**V120 Small is the general restoration and quality-development recommendation.**
Its completed 427-source photo mean is 37.04008 dB, known/unseen measured-CFA means
are 54.31272/54.00872 dB, and tested ADC maximum color bias is 55.52 DN16.
It retains V119's photo gain while recovering its camera/color regressions.
Full panels, saved-output audits, native comparisons and 102MP RGB16 exports are
complete. [Primary evidence and matched-profile full frames](v120-v121-primary.md).
Fine foliage, low-contrast texture, saturated signs and the green mesh still need work.

Architecture follows measured strengths rather than historical promotion gates.
V120 keeps the V84-family pretrained DRUNet RGB trunk, physical noise/camera
conditioning and official frozen DINOv3 ConvNeXt-Small pyramid.
[Implementation and pinned encoder](research.md#foundation-features-and-the-new-objective).

| Use | Useful choice and measured tradeoff |
| --- | --- |
| General RAW and quality development | **V120 Small**: photo37.04008 dB; known/unseen54.31272/54.00872 dB; ADC maximum55.52 DN16; real fine detail remains soft |
| Slightly higher single-view photo mean | **[V117 Tiny](v117-v118-quality.md)**: photo37.04408 dB; known/unseen54.27303/53.97339 dB; higher ADC maximum63.89 DN16 |
| Tiny alternative / lower tested ADC maximum | **[V114 Tiny](v114-v115-quality.md)**: photo36.97973 dB; known/unseen54.28627/54.00290 dB; ADC mean/maximum7.08/51.73 DN16 |
| Slightly higher known-camera mean | **V115 fitted Small**: photo36.97700 dB; known/unseen54.32405/54.00417 dB; ADC maximum65.64 DN16. Its transfer initializer changes along with encoder size |
| Optional eight-view inference | [V114 fixed 24 pilot](v114-eight-view.md) improves all 12 material cases and two selected adverse camera crops, with a selected color-bias tradeoff. Full panels/frame remain unmeasured; eight evaluations per tile |
| Optional ADC observed-sample fidelity | [V114 sites export](adc-consistency.md) improves427-source ADC photo PSNR37.78013→38.01575 dB and worst color bias51.73→37.82 DN16, with higher flat-field spatial RMS. Positive-noise profiles bypass it |

These finite comparisons do not establish a universal ranking. Tiny/Small
weak natural-detail response is nearly unchanged on the same 427-source support;
encoder size alone does not resolve it. [Full local diagnosis](local-material-detail.md).
The [fixed V115/V117 output mean](fixed-tiny-small-mean.md) gives an intermediate
tradeoff without a clear visible GFX improvement.

The completed [V163 phase-input trial](harmonic-phase-inputs.md) lowers mean quiet RMS **0.62–1.19% versus V162** through 2.60–3.96% lower color bias. Spatial error rises slightly, mesh response falls another 0.52–0.59%, and all 48 coarse-flat errors worsen versus V162. Native fence crossings remain soft. All four endpoints, 822 cases, 72 actual native views and independent audits are complete; 180 CPU checks, 93 final Adam states and exact controls pass. The disk-guard failure and verified 268-call adoption are preserved.

The completed [V164 weak-pair floor trial](pair-unit-floor.md) gives **8.35–12.32% more mesh response and 0.28–0.52% lower coarse flat error versus V163**, changing only the pair-loss unit floor from16 to2 DN16. All48 native512 coarse inputs improve at both endpoints. Total-flat RMS rises0.27–0.39%, quiet means rise0.20–9.85%, and all32 quiet spatial errors worsen; real fine cab crossings remain incomplete. Both1k heads/four endpoints/822 cases/72 actual native figures and independent audits are complete. All199 CPU checks,94 final Adam states, exact V163 controls and all1,000 actual unit records pass. Retain the response/coarse gain beside earlier quiet/grain/total-flat strengths.

The completed [V165 pair-common trial](pair-common-error.md) lowers native512 full-flat RMS **1.35–1.91%** and quiet spatial RMS **6.22–8.69% versus V164**. Mesh response falls 49–50% to parent level, and quiet color bias rises 7.67–28.07%; real crossings remain weak. Retain the grain/total-flat option beside stronger V161/V164 detail and V158 quiet accuracy. Both 1k heads, four endpoints, 822 cases, 72 actual native figures and independent audits are complete; 221 CPU checks, 94 final Adam states, exact controls and all 2,000 recorded weighted loss totals pass.

## Run the current model

[Inference, hot-pixel repair and linear DNG/JPEG usage](usage.md) reads the
[explicit current selector](../configs/current-model.json).
V120's checkpoint is `/mnt/external/demosaic/models/v120-final20000.pt`, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.

Available alternatives retain exact identities:

| Checkpoint | SHA256 |
| --- | --- |
| `/mnt/external/demosaic/models/v117-final20000.pt` |`f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0` |
| `/mnt/external/demosaic/models/v114-final20000.pt` |`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2` |

[Endpoint aliases](results/v120-v121-endpoint-aliases-v1.json) and the
[V120 selection receipt](results/current-model-v120-selection-v1.json) preserve
the original checkpoint and prior selector evidence. New experimental data do
not silently change an existing run's parent, schedule or input snapshots.

## Quality and remaining work

The current [training pipeline](training-pipeline.md) uses native 256/B16,
geometry before final area reduction and zero optical PSF augmentation.
The newest prepared dataset has 90,773 photos/37 reviewed regions. The
[latest source inspection](v125-v131-source-review-5600-9800.md) withholds one
grainy coastal source and adds mixed leaf detail while preserving all 36 prior
region objects. V134/V135 retain their 33-region bank; active and queued
comparisons keep declared cohorts. A
[full source-schedule audit](training-source-schedule-coverage.md) distinguishes
corpus size from the identities actually selected in 20k planned updates.
The optional [photographic epoch order](photographic-epoch-order.md) achieves
full source visitation on the prepared set at that budget; trained quality
under this new ordering remains unmeasured.

| Quality question | Current evidence and action |
| --- | --- |
| Wider initial matching samples | [Completed V174](spread-sample-matching.md): only five offset bias vectors change at fixed V172 model/loss/data. Six observed coarsest p90 distances remain about 90.7 native pixels versus 12.04 for V172. EMA quiet total −0.12–0.17%, spatial −0.04–0.08%, DC −0.36–0.43%; mesh response −0.25% to 3.868% of GT. Flat/coarse changes mixed; mottle and crossings persist. Both endpoints/822 cases/60 native figures and scoped audits complete. Separate six-input V175 path removal changes 18–84% of the small added correction, rejecting complete bypass on those inputs without isolating distant information |
| Amplitude-balanced gradient loss | [Completed V173](weak-gradient-matching.md): same V172 network/data/optimizer, only gradient term changes. EMA quiet spatial RMS −0.32–0.68% on all 32 inputs, quiet total −0.27–0.52%, full-flat −0.25–0.30%; mesh response −3.95% to 3.724% of GT and natural band response −2.63–2.88%. Mottle/crossings unresolved. Both endpoints/822 cases/60 native figures, 162 focused checks and scoped audits complete. Quiet variant; V172 remains the matching baseline for detail work |
| Local matching noise units | [Completed V172](local-noise-matching.md):same2.09M network/initialization/cache/loss as V171,local feature/output units together. EMA quiet RMS −0.31–0.77%, DC −1.33–2.55%,mesh response +1.06% to3.877% of GT versus V169; much less V171 added cast. Flat gains only0.059–0.085%,absent RMS +0.060%;mottle/crossings unresolved. Both endpoints/822cases/60 native views,126 tests and scoped audits complete. Useful local-unit variant;retain V171 flat and V161 detail strengths |
| Fresh matching residual capacity | [Completed V171](learned-matching-residual.md):2.09M parameters above frozen V169/DINO, trained on the same free-image/synthetic cache. EMA full-flat RMS −1.21–1.52%, coarse RMS −1.73%, all 48 inputs improve; mesh response +1.26% to 3.885% of GT. Quiet RMS +26–31%, DC bias +91–93%, visible casts and missing real crossings remain. Both endpoints/all 822cases/60 native figures complete;114 CPU tests,900 updates,actual checkpoint restoration and 144 exact ADC bypasses. Useful flat option; context-dependent color error remains unresolved |
| Learned nonlocal RAW matching | [Completed V170](nonlocal-raw-comparison.md): released15.28M-parameter NLFeMF, direct Malvar and DINO-parent residual reconstruction from one RAW call. Coarse native512 error −15.79–19.38% versus V169 EMA; quiet spatial error lower. Mesh response falls to2.406–2.533% of GT; quiet total/DC error rises, low-noise periodic artifacts and missing cab crossings persist. All822 cases/60 native figures complete;13 CPU tests, exact original-class parity and independent sampler/selected-array checks pass. External training-data comparison; no matched training or broad superiority claim |
| Broad direct RGB corrections | [Completed V169](balanced-spatial-correction.md): fixed V168 weights,Gaussian complement of direct RGB at sigma8/radius24 native pixels; full spectral path retained. Quiet RMS −3.74–10.69%,DC color bias −11.45–31.59%; mesh response stays3.806–3.837% of GT. All48 coarse-flat errors worsen; total-flat means +0.389–0.705%,quiet spatial +0.167–0.267%,local mottle/real crossings remain. Both endpoints/822cases/72 native views complete;47 CPU checks,six CUDA filter cases,1644 exact replays. All-case streamed metrics;posthoc full-array audit limited to36 saved native cases. Useful response/quiet-color option with flat/grain costs |
| Fine-mesh training distribution | [Completed V168](fine-mesh-training.md): same V167 architecture/losses/init;171 finer-wire/contrast-ladder batches and829 exact old inputs/parents. Mesh response +17.48–18.09% to3.805–3.836% of GT; finest crossed recipes gain about59%,still1.8% of GT. All48 coarse-flat errors improve. Quiet RMS +1.49–5.44%,all32 spatial errors worse; total-flat means +0.136–0.228%,real crossings incomplete. Four endpoints/822cases/72 native views/audits complete;288 CPU checks,94 Adam states and exact V167 control reproduction. Retain data gain beside earlier detail/quiet/flat strengths |
| Bounded spectral support | [Completed V167](bounded-spectral-support.md): shifted quarter-floor mapping at identical124909-parameter heads/data/init/loss/routing. Mesh response +47.33–47.55% versus exact V166 controls,to3.24–3.25% of GT; present RMS −1.09–1.15%. Quiet RMS +2.84–3.74%,all32 spatial errors worse; full-flat means +0.189–0.382%,coarse means slightly lower. Real fine crossings remain incomplete. All256 mesh support means stay near.25;coefficient RMS adapts downward. Retain useful bounded-path response beside V166 quiet color,V165 grain/flat and stronger V161/V164 detail. Four endpoints/72 actual native figures/audits complete;266 CPU checks,94 Adam states and exact controls |
| Common-loss support routing | [Completed V166](common-support-routing.md): identical inference/124909 parameters/47 tensors,common loss values and weights. Only its candidate backward route holds support fixed. Quiet RMS −6.10–15.27% and DC bias −17.52–31.30% versus V165;27/32 raw and24/32 EMA quiet inputs improve. Mesh stays near parent2.20% of GT,all256 mean gates below1e-4;all48 coarse errors worsen versus V165. Full-flat/coarse still improve on46/48 and48/48 inputs versus V143,but quiet means remain above parent. Retain quiet-color option with persistent mottle/detail limits. All endpoints/72actual figures/audits complete;238 CPU checks,94 Adam states,exact V165 control;failed telemetry prefix preserved |
| Absolute pair-common targets | [Completed V165](pair-common-error.md): only added common-error loss weight0/1 differs at fixed V164 heads/data/optimization. Full-flat means −1.35–1.91%; quiet spatial −6.22–8.69%, all32 inputs better versus V164. All48 full/coarse flats improve versus V143. Mesh response halves to2.196–2.201% of exact GT, quiet DC bias rises7.67–28.07%, and raw quiet total error worsens. Native crops show less grid/grain but persistent casts and weaker real strands. Archived mean support is below1e-4 on all256 present-mesh cases; this post-hoc metadata is not causal proof. Retain grain/total-flat option beside stronger response/coarse/quiet choices. Four endpoints/822cases/72actual views/audits complete;221 CPU checks,94 Adam states, exact V164 controls and2000 actual FP32 objective reconstructions pass |
| Stronger supervision for weak pairs | [Completed V164](pair-unit-floor.md): identical47-tensor/124,909-parameter V163 heads and cache, pair-unit floor16→2DN16. Response +8.35–12.32%, reaching4.298–4.429% of GT; all48 native512 coarse errors improve, means −0.28–0.52% versus V163. Raw approaches V157 coarse strength. Full-flat means +0.27–0.39%, quiet means +0.20–9.85%; all32 quiet spatial errors worsen. Native cab crossings remain incomplete and amplified quiet casts persist. Retain measured response/coarse option beside V161 response/V162 grain/V163 bias/V158 quiet/V160 ordinary total-flat strengths. All endpoints/822 cases/72 actual native views/audits complete;199 CPU checks,94 Adam states, exact control trace/states/1644 outputs and1000 independent actual-unit records pass |
| Cross-frequency phase inputs | [Completed V163](harmonic-phase-inputs.md): at fixed V162 data/loss, sixteen phase coordinates and512 extra parameters lower mean quiet DC bias2.60–3.96% and total quiet RMS0.62–1.19%,with individual regressions. Spatial means rise0.025–0.185%,mesh response falls0.52–0.59%,and all48 coarse-flat errors worsen versus V162. Native crossings remain soft,broad mottle persists. Retain the small measured bias option beside stronger V161 response/V162 grain reduction/V158 quiet/V157 coarse/V160 ordinary total-flat strengths. Four endpoints/822 cases/72 actual native views/audits complete;180 CPU checks,93 final Adam states,exact control states/1644 outputs and1000 masks pass. One disk-guard review failure and explicit268-call adoption/3020-call continuation preserved;no completed call repeated |
| Absolute supervision on clean flat regions | [Completed V162](flat-target-anchor.md): extra target anchor at fixed V161 architecture/data/base losses reduces quiet spatial RMS 4.73–7.73% on all 32 inputs; total quiet RMS falls 1.68–5.29% with six regressions. Native512 flat RMS falls 1.28–2.55% versus V161, but mesh response falls 20–22% to 3.846–4.112% of GT and ISO12800 mean quiet bias rises. Less fine colored grain, persistent mottle/casts and soft real crossings. Both heads/four endpoints/822 cases/72 actual native views and audits complete; 156 CPU checks, 92 final Adam states, exact V161 controls and all 1,000 mask checks pass. Retain the grain-reduction option beside V161 response/V158 quiet/V160 ordinary total-flat strengths |
| Distant frequency evidence | [Completed V161](harmonic-frequency-context.md): mesh response +20.56–21.57% versus exact V160 paired control, reaching 4.83–5.24% of GT. All 48 coarse flat errors improve;quiet RMS +4.99–7.37% versus control and 14.14–18.38% versus V143. Native strands gain modest contrast;crossings soft,false colored/gridded grain and bias increase. Stronger learned-detail capacity prototype;retain V158 quiet/V160 ordinary total-flat/V157 coarse strengths. Four endpoints/822 cases/72 actual native views,independent audits and 48 diagnostic calls complete; 139 CPU checks, 91 final Adam states, all 1000 control trace/state/1644 output replays exact |
| Paired weak-detail response | [Completed V160](paired-response.md) raises learned mesh response 82–96% over V143, reaching 4.00–4.31% of exact GT. Blank RMS rises 3.25–4.69%, quiet RMS 8.46–11.36%; native views show extra colored grain and slightly stronger existing real mesh strands, with soft crossings. Response supervision retained in V161; preserve V158 quiet and V157 coarse strengths. Both heads/four endpoints/822 cases/72 actual native views and independent audits complete; 123 CPU checks and 450 exact frozen-base parameter gradients pass |
| Paired-data ordinary control | [V160 ordinary](paired-response.md) improves native512 full flat RMS 0.42–0.53% versus V143; all 48 full/coarse inputs improve at both endpoints. Quiet RMS instead rises 0.76–1.58%, with 18/32 raw and 17/32 EMA regressions. This changes the full data/noise recipe versus V159; only its matched V160 pair-loss contrast isolates weight0 versus1 |
| Persistent detail bias | [V12420k native check](v124-final20000-native.md) gives ordinary+.0095dB/faint−.0856dB versus V120; faint spatial MSE is only0.39% higher after late recovery from14k. Real mesh remains weak. [V1256k](v125-progress6000-quality.md) is still1.009dB below V120 on faint contexts. Limited and unequal-budget supports; original matched full endpoint/bias review remains pending |
| Spatial RAW detail | [V131/V132](raw-spatial-training.md) tests a22,664-parameter branch on90781/29. [V131 control at1k](v131-progress1000-quality.md) gives ordinary+.0016dB, deepest shadows−.0237–.0342dB and faint ADC−.2734dB versus V120, with mixed local detail and no clear mesh recovery. V131 stopped at step14,549; V132 production/full endpoints remain unmeasured |
| Global RAW repetition | [Completed V1361k](v136-global-attention-quality.md) adds18,272 parameters for two-pass global attention. Against matched V129: ordinary+.0003dB, shadows+.0007–.0026dB, faint ADC+.0131dB; local gains/errors are mixed and real mesh remains weak. Full native comparison and independent audits published |
| Conditioning global matching | [Completed V1371k](v137-global-conditioned-quality.md) gives faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and weak real mesh. A [trained-memory ablation](global-memory-contribution.md) finds only0.83–1.39% feature-offset change on six contexts despite varied attention; it does not measure final RGB influence |
| Adapting only the global branch | [Completed V1381k](v138-quality.md) freezes all 91 parent model/EMA tensors and trains 18 branch tensors at LR1e−3. Faint ADC +.00406 dB and noisy-flat spatial RMS −.15% versus V120; no clear new mesh recovery. All 150 inputs/audits/native views complete |
| Removing the global branch's local bypass | [V139](raw-global-memory-only.md) retains15 memory-path tensors with the V120 parent frozen. CPU/CUDA16+2 checks pass; original1k remains unstarted after the original dependency failure. V138 recovery does not launch it; quality remains unmeasured |
| Separate gradient-error smoothing | [V141](v141-gradient-epsilon-pilot.md) changes only gradient epsilon3e−4→3e−5: faint ADC+.01528dB versus V129, mixed local detail and no new mesh recovery; noisy-flat coarse error near V129 and5.75% above V120. Default remains inherited pixel epsilon |
| Crossed-line and empty training targets | [Completed V142](v142-crossed-line-pilot.md): faint ADC+.05212dB and noisy-flat spatial RMS−4.55% over V129, with selected weak grass/wood gains. Coarse noisy error stays5.08% above V120; ADC-only DC bias worsens. Useful further-training data, no new mesh recovery |
| Comparing neighboring gradients before memory | [V140](raw-patch-memory.md) adds2,048 zero-initialized descriptor parameters. Standalone1k/102-input native/faint/GFX and 48-flat reviews complete: ordinary+.00003dB/faint−.00015dB over V120, no clear mesh recovery, near-parent flat/sky variation |
| Photographic variety at fixed budget | [V133](reviewed-quota-training.md) lowers V131's reviewed quota from50% to5% with the same parent/data/20k horizon. CPU/CUDA16+2 checks pass; original production/review dependency queues exited; trained quality remains unmeasured |
| Cleaned corpus and source visitation | [V134/V135](photo-epoch-training.md) compares replacement/epoch ordering on identical90,778/33 data. All four CPU/CUDA16+2 checks pass; original20k production/full-review dependency queues exited; trained quality remains unmeasured |
| RAW frequency features | [Completed V122/V12320k trial](v122-v123-quality.md): joint-arm photo gain+.05493 dB over adapter-only, with lower unseen-camera mean, ADC maximum4190.02 DN16 and little weak natural-detail or real-mesh recovery |
| Larger Fourier window and more mesh exposure | [V146 at 500 updates](v146-coherent-frequency.md): frozen V143 parent, native256 Fourier support and 1,246 present/1,183 empty training meshes. Raw/EMA response+.62%/+.44%, but mesh/photo errors rise and native detail remains missing. [Matched inference-window transfer](v146-window-transfer.md) to native512 support also gives no useful gain, with 72 actual512 flats and 32 native figures. No replacement for V143/detail |
| Direct late RAW innovation | [Completed V1471k](late-spectral-detail.md): mesh response−8%, noisy-flat error+.24–.34%, no clear new real mesh or organic detail. Strong-edge whole-scene RMS improves .31–.42% while quiet patches worsen. All 64 native figures/audits complete. Removing local support exposes a worse frequency proposal; the component remains for research |
| Bounded complex CFA mixing after parent | [Completed matched V1481k](phase-matrix-detail.md): scalar control exactly reproduces V147; matrix response falls8–9% against V143, with higher photo-band and native512 flat errors. Small strong-edge/full256-flat gains coexist with worse quiet patches and missing native green-mesh/feather detail. All four endpoints,58 figures and audits complete; research component, no improved model recommendation |
| Spectral capacity and local flat safety | [Target-informed diagnostic](spectral-capacity-oracle.md): bounded per-bin matrices can express much stronger detail with GT, but full support can invent a quiet-region lattice beside stripes. Oracle outputs are unavailable at inference; they relax shared-network coupling. Compare actual blank/DC/spatial error alongside correction energy, which can also represent beneficial denoising |
| Known CFA phase and green coherence | [Completed matched V1491k](coherent-phase-estimator.md): alignment modestly improves the native control, but both new arms retain6–7% less mesh response than V143, with no useful new cab-mesh/photo texture. Strong-edge whole RMS gains .45–.74% coexist with worse quiet regions and native512 noisy flats. Tiny dark-photo/native256-flat gains do not restore weak bands. All6 endpoints/66 native figures/audits complete; research components remain available, with no inference integration |
| Training-loss noise scale | [Completed V150](objective-floor-training.md) tests the [diagnosed ADC pressure](spectral-loss-allocation.md): 16 DN reduces ADC clipping35→4, noisy512 flat RMS .045–.047% versus V143 and ADC photo RMS about3.06% on two held-out sources. Mesh response still falls4.3–4.5%; no useful new real wires/noisy organic texture, with quiet/coarse-slope regressions. All4 endpoints/822 cases/72 actual native views/audits complete; native control's trace/weights/Adam/all1596 retained predictions are exact. Use16 DN for the next noisy-head training comparison while retaining2 DN's stronger ADC band/coarse-flat results. No inference integration |
| ADC isolation and noisy peak emphasis | [Completed matched V151](noisy-objective-training.md): noisy-only raises mesh response 3.76–7.22% over V143 and lowers native512 noisy-flat RMS .10–.16%. Absolute response is only 2.28–2.36% of exact GT; quiet errors still rise and real wires/natural texture stay missing. Most ADC photo gains are lost. Peak8 nearly closes support, without useful noisy recovery. All six endpoints/822 cases/84 native views/audits complete; all 1,644 control predictions reproduce V150 exactly. Use noisy-only/16 DN/no peak bonus as the next noisy-head training control; retain V150's ADC strengths. No inference integration |
| Relative phase between RAW and residual | [Completed V152](relative-phase-estimator.md): cross-spectrum inputs raise mesh response 1.27–1.41% over V151 noisy-only and modestly lower noisy-flat error. Response remains 2.31–2.39% of GT; quiet RMS worsens .334–.834% over V143 and natural-band response falls further. No convincing new real wires/organic texture. All four endpoints / 822 cases / 72 native views/audits complete; all 1,644 control arrays reproduce V151 exactly. Keep the new input feature for estimator/support prototypes and V151 as the quieter control; V150 retains stronger ADC photo results. No inference integration |
| Fixed proposal/support diagnosis | [Completed V152 crossover](support-crossover.md): most added quiet MSE follows the relative proposal under fixed original maps. Full support raises response to2.56–2.60% of GT, with worse actual blank/quiet errors and no new convincing real crossings. All six compositions/822 cases/84 native views, independent metric/reconstruction/risk audits and1,644 exact original replays complete. Crosses are two-head diagnostics, not new checkpoints. Test delivered-output spectral supervision next; general inference choices remain V120 and explicit V143 periodic detail |
| Spectral supervision after support/demosaicing | [Completed V153](delivered-spectral-objective.md): mesh response rises6.04–7.97% over matched control to2.45–2.59% of GT, with worse actual blank errors/natural-band attenuation and lost ADC photo gains. Quiet results are mixed; mosaic coarse slope error improves with a DC tradeoff. All three1k heads/six endpoints/822 cases/84 native views/audits complete; all1,644 control arrays are exact. Retain the stronger response prototype beside quieter V151/V152 controls and stronger ADC V150. Real crossings/organic texture remain missing. No general inference default change |
| Robust weak-error supervision | [Completed V154](robust-spectral-objective.md): Charbonnier .01/.003 lowers native512 noisy-flat RMS 0.45–0.50% and present-mesh actual blank RMS 0.21–0.27% versus V143, both better than matched RGB MSE. Broad mottle remains; mesh/natural response weakens and mixed quiet RMS rises 1.51–2.27% versus V143. All three 1k heads/six endpoints/822 cases/96 native figures/audits complete; all 1,644 MSE-control arrays reproduce V153 RGB exactly. All 32 robust ADC photo arrays retain parent values, losing V150 gains. Narrow flat-field strength retained beside stronger detail/ADC and quieter controls; no new general inference default |
| Cleaner research parent | [Completed V155](matched-parent-comparison.md): fresh matched V120/V143, 822 inputs each. V120 lowers native512 coarse noisy-flat RMS 1.59–2.36% but raises total RMS 2.31–5.11%; quiet RMS falls 0.39–0.91% with ISO6400 spatial error higher. ADC photo RMS improves 0.60%, while ADC slope full/coarse error rises 33.26/112.65%. Neither restores fine cab crossings. All 1,644 full outputs/64 native views/audits complete. Retain V143 as matched noisy-detail control and V120's measured coarse/photo strengths; V120 remains the general recommendation on broader evidence |
| Local excess-error supervision | [Completed V156](local-excess-risk.md): local RMS-regret lowers quiet error0.30–0.63% versus matched MSE on all 32 inputs at both endpoints; mean parent-level regression drops71–98% but many cases still regress. Response stays 5.59–10.52% above V143, below MSE. Versus quieter V151, response rises 1.76–3.07% and mean quiet RMS falls 0.03–0.18%, with individual costs. All four endpoints/822 cases/72 native figures/audits complete; control trace/raw/EMA/Adam/1644 replays exact. Local regret remains part of V160/V161’s stronger learned-response prototypes; retain its quieter V156 endpoint, V154 standalone-flat and V150 ADC strengths. Real wires and broad mottle remain unresolved; general V120 choice stays |
| Direct spatial/coarse RGB prediction | [Completed V157](spatial-rgb-residual.md): larger four-scale direct RGB hybrid, same V156 loss/data/schedule. All 48 native512 noisy-flat inputs improve in full/coarse error at both endpoints; full RMS −0.94–1.10%, block32 −0.90–0.98% versus V143. Quiet total RMS +10.26–14.98% despite spatial RMS falling; visible magenta/blue casts and weaker mesh response, no new real cab crossings. ADC photos improve 1.04–1.16% but ADC coarse slopes worsen. Four endpoints/822 cases/72 actual native views/audits complete; exact V156 controls, 45 tests, 58 finite final Adam states. Preserve direct coarse capacity and flat strength beside quieter V156 and stronger V153/V150 controls; general V120 choice stays |
| Regional color-bias supervision | [Completed V158](regional-dc-regret.md): same hybrid/data/base objectives as exact V157, plus regional RGB mean-error regret. EMA quiet RMS −0.09–0.12% versus V143 on all 32 inputs; averages −0.13–0.17% versus V156 EMA, with two individual regressions. Large V157 color casts recede, but standalone-flat full gain shrinks to 0.046–0.053%, block32 about 0.001%; mesh still below V143/V156 and real crossings missing. All four endpoints/822 cases/72 actual native views and audits complete; 56 tests, 90 finite final Adam states and exact control state/1,644 replays pass. Keep the quiet supervision beside V156 detail and V157 spatial/coarse strengths; no combined general winner |
| Smoother near-parent DC pressure | [Completed V159](regional-dc-transition.md): transition1e-4→1 at fixed weight1 reduces clipping726→101/882. Native512 full RMS −0.27–0.39%,block32 −0.17–0.19% versus V143;all 48 coarse inputs improve against V143/V158/V156 at both endpoints. Quiet RMS +0.18–0.48% versus V143,regional bias larger,mesh weaker than V158 and no new real crossings. ADC photos partly recover,ADC coarse slopes worsen. All four endpoints/822 cases/72 actual native views/audits complete;60 tests,90 finite final Adam states and exact V158 states/1,644 replays. Useful modest coarse/quiet compromise;V158 quiet,V156 detail and V157 stronger coarse capacity remain visible |
| Loss or shadow reweighting | [V117/V118](v117-v118-quality.md), [V126/V127](reviewed-shadow-pilot-quality.md) and [V128](v128-feature-pilot-quality.md) find no useful broad weak-detail gain from their tested band, shadow or DINO feature additions. These terms stay off by default |
| More reviewed sources / training precision | [V129](reviewed-detail-training-pilot.md) and [V130](training-precision-pilot.md) show small mixed1k changes without clear noisy/GFX recovery. FP32 improves selected [faint-ADC bands](faint-adc-precision.md), with global PSNR−.01720 dB and subtle native changes |

The [main DSCF3879/3880 gallery](gfx-qualitative.md) includes foliage, fence,
building and sky. The additional [DSCF3842/DSCF3835 fine green mesh](gfx-green-mesh.md)
remains an adverse case under both fixed profiles. ISO100/AHD and camera JPEG
references differ in aperture, exposure time and moving subjects; they are
qualitative references, not exact GT. Both pairs and siblings remain held out.
The [Q2/Sony/GFX50R comparisons](cross-camera-qualitative.md) likewise retain
soft dark rocks/window edges and small differences among recent versions.

The [11-capture binned-reference comparison](native-camera-development.md#v120v121-extension)
finds much finer texture than RawNIND and V120's+3.69903 dB high-noise camera-RGB
gain under added noise. Residual source noise and that limited development
support do not establish broad real high-ISO superiority: stronger released
RawNIND still wins four of nine measured camera scene means. State-of-the-art
quality remains unproven. [Requirements and remaining evidence](requirements.md).

Complete101.996MP FP32 outputs and 16-bit exports are verified. Ordered Tiny/Small
inference/blending observations are 116.57/101.66s; differing warmup/workspace
states prevent a speed ranking. The 100MP/10s target remains open. Hot-pixel
repair and [linear DNG/JPEG export](dng-export.md) are merged; repair was off in
these comparisons. Quality precedes speed optimization.

[PSNR history](performance-history.md) contains56 completed primary endpoints.
Earlier implementation decisions and the exact previous version of this page
are preserved in the [local-time diary](../diary/2026-10-27-08-52-27-source-schedule-coverage.md).
Original study reports, checkpoints and machine receipts remain intact.

The completed [V166 common-support routing trial](common-support-routing.md) reduces quiet RMS **6.10–15.27%** and DC color bias **17.52–31.30% versus V165**, visibly reducing the representative magenta casts. Mesh response stays near the parent and real fine crossings remain incomplete; all256 present-mesh mean supports remain below1e-4. Full-flat means worsen0.199–0.312%,coarse means0.216–0.376%,with all48 coarse inputs worse versus V165. Quiet means remain2.40–6.34% above V143. Retain this quiet-color gain beside V165 flat/grain,V161/V164 detail,V157 coarse and V158 quiet strengths. Both1k heads/four endpoints/822cases/72actual native figures are complete;238 CPU checks,94 final Adam states,exact V165 controls and independent audits pass. Original smoke failure and three discarded calls are preserved;no full-training restart.

The [completed V167 support-floor comparison](bounded-spectral-support.md) recovers
response from V166 at a consistent quiet-field cost. The isolated mapping and
constructor metadata are available in `src/demosaic/late_bounded_support.py`;
all89 prior neural sources remain unchanged. The [cache coverage audit](results/mesh-training-coverage-20261107-v1.json)
motivated [V168's completed fine-family/contrast-ladder test](fine-mesh-training.md).
That data change recovers more fine-family response and lowers coarse-flat error,
while increasing quiet and total-flat errors. It preserves all90 V167 neural
sources; frequency and contrast change jointly,so their individual effects remain
unresolved. More response alone does not establish accurate real crossings or
safe quiet fields.

The [V169 fixed-weight branch comparison](balanced-spatial-correction.md) now
separates a useful part of that tradeoff: broad direct RGB corrections provide
much of the added quiet DC bias and much of the standalone coarse-flat gain.
Removing that broad component retains mesh response while reducing color bias,
but slightly worsens quiet spatial error and increases total/coarse flat error.
This supports further work on conditional coarse correction; it does not prove
that broad correction is always harmful or that residual splotches are gone.

The [V186 read-only frequency diagnostic](frequency-selection-coverage.md)
finds 90.08% of clean green-CFA template power already inside the current band,
but only 21.25% mean / 1.18% median proximity to input-selected bins. Broadening
at the same candidate count helps little. Strong global peaks also occur beside
uniform quiet ROIs. These are diagnostic fractions, not recovery bounds or
confidence. The completed [V187 pooled-selection trial](pooled-phase-wave-comparison.md) improves mesh and quiet means at the same parameter/training budget, while slightly worsening absent/flat controls. Pooling and rank allocation change together; neither phase is now a selection holdout.
The [V188 allocation diagnostic](spectral-selection-diversity.md) found better weak-sector proximity with wider suppression, with unchanged whole-template median, lower tighter proximity and higher local quiet powers. The completed [V189 matched model test](spaced-pooled-wave-comparison.md) regresses on mesh/quiet quality, demonstrating that this proximity gain is not a reliable quality proxy. V187 remains preferred.


The [V192 measurement-support calculation](dense-measurement-support.md) separates taper support from carrier-grid error. In its fixed analytic cases, Hann65 retains 23–48% of rectangular65 SNR power with nearest carriers; Hann129 retains 112–176%. This motivates a larger-window test, not a learned quality or flat-safety claim. No image/model inference or neural source changes occur.


The completed [V193 larger dense window](large-dense-spectrum-comparison.md) raises mesh response **1.72% raw /1.50% EMA** over matched V191 to **4.556% /4.540% of exact GT**, with quiet spatial RMS **0.285–0.707% higher**, worsening31/32 inputs in each state. Response remains **12.84% /15.29% below V187**, and real fine crossings remain incomplete. Retain the measured dense-response gain and its quiet cost; V187 remains preferred wave and V120 Small general. Both endpoints, audits,60 viewed native figures/12 triplets and two exports are complete. [Twenty-two-state viewer](images/v193-large-dense-v1/native-viewer.html) · [Exact evidence](results/v193-large-dense-final-v1.json).

The [V194 directional check](mesh-directional-response.md) finds a hidden imbalance in the fixed mesh2309 example: V187 EMA has79.24% whole-template response but4.82% /91.69% in its two spectral regions, with85.67% of GT energy in the stronger region. Mesh2302 stays weak in both. This two-example saved-output diagnostic motivates testing balanced response pressure, without claiming a new model, isolated wire-family amplitudes or flat safety. [Audited, actually viewed evidence](results/v194-orientation-response-completed-v1.json).

The [V195 balanced directional response loss](directional-pair-response.md) passes 26 CPU contracts, 53,477,376 saved-output gradient coordinates and GPU/head-state admission. Both matched whole-pressure/directional-pressure arms completed 900 updates from the same V187 EMA donor with fresh identical optimizer clocks. The full independent audit passed 2,000 rows, ten checkpoints and 3,780 inherited tensor comparisons. Four-endpoint evaluation is running; all 822 cases per endpoint and native protected-GFX/flat comparisons remain required before a quality conclusion. All 103 neural sources and current model choices remain unchanged. [Completed training/state evidence](results/v195-response-training-completed-v1.json).
