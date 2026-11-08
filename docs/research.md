# Current method research

The [V178 native CUDA admission](phase-evidence-admission.md) is prepared and
waiting behind V175's complete GPU pipeline. It will check actual zero-adapter
output parity, CPU/CUDA features, all 142 gradients, checkpoint/Adam/RNG restoration
and post-update ADC/mixed-zero invariants. All 18 CPU launch-protocol tests pass;
the frozen worker entry rejects the current live dependency before Torch import.
This is implementation preparation; V178 has no trained-quality result yet.

The [V178 phase-evidence matching path](phase-evidence-matching.md) makes the
V177 observations available to the matching network as continuous features.
Four A-selected frequencies per green direction provide 80 wave/power/signed
cross/frequency maps; a zero 3,120-weight projection adds them to the existing
39 matching coordinates. This differs from another spectral descriptor in the
already frozen component: the matching branch can directly use the measured
waves while learning spatial support. It introduces no hard detection threshold
or direct sinusoid-to-RGB correction. All 68 CPU checks and native feature/strict
checkpoint probes pass, with the original FP32 phase-angle failure preserved.
The model is untrained; CUDA behavior, actual matching gradients, detail recovery
and noisy-flat costs remain unmeasured. V175 continues unchanged.

The [V177 within-image CFA sample split](phase-frequency-evidence.md) closes a
specific diagnostic gap: one green RAW phase selects an unknown frequency and
the other measures it, with GT entering only afterward. Primary nominal power≥16
occurs in 170/614 present and 0/614 matched absent training cases. At≥4, six
absent cases pass; considering eight candidates raises that to 71. This suggests
using continuous repeatability evidence, with no calibrated detector or safe
restoration claim. A strict power16 gate misses 204/374 cases whose V176
conditional green SNR is≥5, and negative principal-band agreement occurs on
reference-supported peaks. Native aliases, spatial support and weak evidence
must be preserved rather than treating one signed spectral statistic as truth.
All 33 CPU checks and independent QR/DFT verification pass; no model is trained.

The [V176 training-template diagnostic](mesh-template-evidence.md) measures
conditional evidence in all 614 retained noisy mesh pairs. Green median
known-template SNR rises from 0.653 in the best native16 window to 7.360 over
native512; all-CFA medians rise from 0.893 to 10.502. Small-window evidence is
often weak even with an exact template. This motivates investigating useful
aggregation over larger areas, but hidden template/background/variances are
supplied. It proves neither inference recoverability nor flat safety, and does
not measure the existing model's receptive field. V143's matched training
Bayer-sample amplitudes also remain weak on many high-conditional-SNR cases;
these are not the held-out RGB mesh metrics. Sixteen CPU tests and independent
QR/variance checks pass, with no model/noise calls or restored RGB. V175's fixed
recipe remains unchanged and its quality pending.

The [V175 fresh-noise continuation](fresh-noise-matching.md) tests a longer
training recipe at V172's unchanged model and seven-term objective. It starts
from the actual raw/Adam/EMA states, adds 8,100 updates and regenerates physical
sensor noise with exact new V143/DINO parents on 8,073 batches. Three clipped
photo rows per pass retain their original observations/parents rather than
substitute a clipped target for clean sensor data. The full 1,000-row preflight
and 54 focused tests pass. Its budget, fresh realizations and reheated learning
rate change together; individual effects are not isolated. Training has
launched, quality is pending, and V172 remains the matching baseline.

The final comparison now includes all 822 saved V161 EMA outputs, re-reduced on
identical inputs/parents/ROIs and current metric bytes. All 8,038 comparable old
scalars reproduce exactly without inference: 5.240% GT mesh response, with
quiet RMS 4.616/7.061 DN16 and full-flat RMS 19.024/24.867 DN16. The stronger
learned detail option and its quiet/flat costs remain explicit.
[Baseline audit](results/v175-V161-baseline-metric-audit-v1.json).
The [prepared postprocessing](results/v175-postprocess-preparation-v1.json)
uses the existing V172 label-corrected scores and freezes nine-method tables,
60 native figures and strict exports before any new candidate quality.

The [completed V174 spread-sampling experiment](spread-sample-matching.md)
retains wide matching positions: six observed coarsest p90 distances are about
90.7 native pixels versus 12.04 for V172. EMA quiet total RMS falls
**0.12–0.17% versus V172**, spatial RMS 0.04–0.08% and DC error 0.36–0.43%.
Mesh response slips **0.25% to 3.868% of GT** and natural band response slips
0.016–0.023%. Flat changes are mixed; broad mottle and missing real crossings
persist. All 822 cases/both endpoints/60 native figures, 133 CPU checks and
scoped audits complete. V172 remains the balanced matching baseline. Wider
sample positions alone did not improve detail in this 900-update schedule.
The initialization also changes tanh optimization conditioning; a single seed
does not isolate geometric reach. [Native-pixel viewer](images/v174-spread-matching-v1/native-viewer.html).

A separate [V175 functional shortcut probe](results/v175-local-shortcut-diagnostic-v1.json)
removes the whole matching path at the final fusion on six selected V174 EMA
inputs. Six existing head/tail paths run without the sampler or frozen/parent
forwards. The change has 18–84% of the full added correction's RMS, while that
correction is only 0.20–0.22 DN16 RMS. This rejects complete matching bypass on
these inputs, but does not isolate distant information or explain under-recovery.
No V175 model is trained. Saved corrections/compositions pass independent checks.

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

V172's local input/output units retain the response/quiet-color compromise used
as the next matching baseline. V173's changed gradient units and transition
reduce quiet spatial error while weakening synthetic mesh and natural band
response. V174 retains wide sample positions without recovering crossings;
the V175 probe finds a nonzero matching-path contribution on its selected inputs.
The next useful question is whether matching learns content correspondence and
enough corrective amplitude under a better training schedule or aggregation
rule. Test that directly with paired detail and absent/quiet controls, natural
bands and both protected scenes. Existing results do not establish that longer
training, stronger gradients or wider offsets will solve the remaining bias.

The [completed V171 matching residual experiment](learned-matching-residual.md)
trains a fresh 2.09M network above frozen V169/DINO on the existing free-image and
synthetic pairs. EMA full-flat RMS falls 1.21–1.52% and coarse RMS 1.73% versus V169,
with all 48 inputs improving in both measures. Mesh response gains1.26% to 3.885%
of GT, while quiet RMS rises 26–31% through91–93% higher DC error. Native crops
confirm stronger purple/blue casts and missing real crossings. More capacity
at this schedule gives a measured flat option, not the requested combined gain.
Zero supplied variance retains V169 exactly; released V170 weights are unused.
Both endpoints/all 822cases/60 actually viewed figures and scoped audits complete.
The local-unit retraining above tests a joint feature/output change beside
bright structure; it does not isolate individual causes of the color error.
A [posthoc saved-array diagnosis](results/v171-selected-native-scaling-diagnostic-v1.json)
finds that local noise attenuation helps the selected quiet crops more than
global RGB-mean removal, but neither beats V169. This supports a local-unit
experiment; it does not establish a full-cohort improvement.

The [V170 external checkpoint comparison](nonlocal-raw-comparison.md) tests the
[April2026 NLFeMF paper](https://arxiv.org/abs/2604.17453) and its pinned release.
It supplies learned RAW matching/filtering with actual noisy-input variance,
then compares direct Malvar and a DINO-parent interpolation residual. Native 512
coarse error falls 15.79–19.38% versus V169 EMA and quiet spatial error falls, but
mesh response drops to 2.406–2.533% of GT, quiet color error rises and low-noise
controls acquire a periodic pattern. Both cab priors still miss crossings.
The port/kernel parity passes; this result motivates matched free-image training
and low-noise identity controls, not a claim that nonlocal matching cannot help.
All 822 cached cases and 60 native figures are complete; posthoc array checks
cover36 selected cases. No new training, parent/DINO, source or noise draws.

The completed [V169 branch intervention](balanced-spatial-correction.md) uses
fixed V168 raw/EMA weights to isolate direct RGB and spectral contributions.
Direct-only response stays near the parent,while its coarse corrections help
standalone flats and add quiet DC bias. A fixed sigma8 Gaussian complement of
the direct correction lowers quiet RMS3.74–10.69% and DC bias11.45–31.59%,with
essentially unchanged3.806–3.837% GT mesh response. It also raises full/coarse-flat
error and quiet spatial error; actual crops retain local blotches and missing
fine crossings. This functional result motivates conditional coarse correction,
not a claim about why training learned the behavior. Both endpoints/all822 cases/
72 native views are complete. New outputs are streamed and fingerprinted;posthoc
full-array checks cover36 retained native cases. No new training,source/noise or
parent/DINO work was used;original V168 outputs replay exactly1,644 times.

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

The [direct RAW refit study](raw-phase-refit.md) tests whether fitting physical
measurements can reduce blurred-support leakage. Eleven development settings and
a new 64-recipe/512-forward validation find a small tradeoff: 7.7% less mean blank
spill with 0.5% lower response and slightly higher image error. The native tail
still leaks; coarse solves cap. A reproducible research script and all comparisons
are retained, with no ordinary inference or learned-weight change.

The [connected wave-support experiment](sparse-phase-support.md) adds group-sparse
selection, removes small components and refits coefficients without the group
penalty. An initial 96-recipe holdout exposed a false stripe island and became
development data. The final independent 64-recipe review adds 512 further neural
calls: response +12.8%, mean added blank RMS −34.0% versus refined TV, with worse
worst-case spill. Native amplified failure/tail controls show both the fixed
island and remaining boundary leakage. The `sparse` mode is opt-in.

The [continuous frequency fit](offgrid-phase.md) addresses FFT-bin mismatch before
TV smoothing. Active measured-green waves get a bounded search; the detector and
original inactive gates are preserved. A locked 64-recipe review adds 512 neural
calls, with 3.7% higher template response, slightly lower texture error and 8.5%
higher adjacent-blank RMS. All absent cases and 4,096 extra flat-noise selector
draws bypass. Centred mesh changes are clearer; full-grid gains are smaller.
Unverified highlights and runtime remain.

The [TV phase envelope](edge-phase-envelope.md) smooths local sine/cosine
coefficients while allowing sharper support changes. Both real mesh families are
clearer without lowering the frequency threshold. Fresh dark recipes show 48.8%
less mean added blank structure than the Gaussian complex fit, with slightly
higher texture error and some blank regressions. The wider sky stays unchanged;
highlight color, bounded-solver accuracy and speed remain open. `edge` is retained explicitly; `detail` is the
current optional-stage default; earlier `complex` and `scalar` modes remain available.

The [local phase-aware correction](local-phase-harmonic-patch.md) makes fine
mesh more visible on V143 while reducing the original harmonic correction's
partial-texture spill. The [optional full-image implementation](phase-harmonic-inference.md)
now runs actual102MP RGB16 outputs under both mesh priors. Soft diagonals improve;
the crossing family remains weak, window positions matter and CPU refinement
adds substantial time. The wider tested sky retains every parent pixel.

The [completed V1435k review](v143-final5000-quality.md) improves faint ADC
PSNR0.26493dB and noisy-flat spatial RMS4.64% versus V120. Coarse error remains
2.63% higher and ADC-only spatial RMS12.85% higher. No clear new real mesh
recovery from training alone; the genuine original endpoint and all reviews
are complete. The [mixed-batch diagnostic](crossed-line-loss-gradients.md)
measures output derivatives and does not attribute trained quality.

The [completed V1411k gradient-loss review](v141-gradient-epsilon-pilot.md)
recovers.01528dB faint ADC PSNR over matched V129, but has mixed local-band
changes and no new fine-mesh recovery. Added matched V129 flat controls show
about5.8% more coarse noisy-flat error than V120 in both continuations.
The [completed crossed-line/empty trial V142](v142-crossed-line-pilot.md)
recovers.05212dB faint ADC and lowers noisy-flat spatial RMS4.55% over V129.
Selected weak grass/wood response improves, with mixed fur bands, no clear new
mesh recovery, coarse noisy error5.08% above V120 and worse selected ADC-only DC bias.

**[V120 Small](current-model.md) is the current general baseline.** It keeps
V84's pretrained DRUNet RGB restoration trunk with physical noise/camera
conditioning and official frozen DINOv3 ConvNeXt-Small spatial features.
Its completed full427 photo mean is37.04008dB, measured known/unseen-CFA means
54.31272/54.00872dB and tested ADC maximum55.52DN16.
[Primary results and native comparisons](v120-v121-primary.md).
V117 has a slightly higher single-view photo mean; V114 Tiny has lower tested
ADC maximum. Architectural choices follow their measured strengths rather than
historical promotion gates. Fine natural detail and real-camera blotches remain
unresolved; broad state-of-the-art quality is unproven.

The [controlled mesh/empty response test](crossed-line-response.md) adds64 fixed
procedural inputs shared acrossV120/V142/V1432.5k. ADC mesh gain stays near.90,
ISO6400-prior gain nearzero. Oracle RAW fits find coherent evidence in the two
clearest recipes; this is not blind recoverability or natural-texture quality.
The noisy failure occurs within the generator family as well as real photos.

The [local phase-aware correction](local-phase-harmonic-patch.md) retains the
input-only frequency/CFA fit but estimates support from local green-phase evidence.
It improves the new active recipe's response and full-patch error while reducing
added field in blank regions62% versus the first harmonic correction. Only one
of16 new recipes activates; all absent inputs remain unchanged. Both standing
GFX scenes/priors/JPEGs are reviewed on actualV1435k, preserving its96-photo/48-flat
values. Remaining spill and missing full-frame support keep this experimental.

The completed [V163 phase-input trial](harmonic-phase-inputs.md) lowers mean quiet RMS **0.62–1.19% versus V162** through 2.60–3.96% lower color bias. Spatial error rises slightly, mesh response falls another 0.52–0.59%, and all 48 coarse-flat errors worsen versus V162. Native fence crossings remain soft. All four endpoints, 822 cases, 72 actual native views and independent audits are complete; 180 CPU checks, 93 final Adam states and exact controls pass. The disk-guard failure and verified 268-call adoption are preserved.

The completed [V164 weak-pair floor trial](pair-unit-floor.md) gives **8.35–12.32% more mesh response and 0.28–0.52% lower coarse flat error versus V163**, changing only the pair-loss unit floor from16 to2 DN16. All48 native512 coarse inputs improve at both endpoints. Total-flat RMS rises0.27–0.39%, quiet means rise0.20–9.85%, and all32 quiet spatial errors worsen; real fine cab crossings remain incomplete. Both1k heads/four endpoints/822 cases/72 actual native figures and independent audits are complete. All199 CPU checks,94 final Adam states, exact V163 controls and all1,000 actual unit records pass. Retain the response/coarse gain beside earlier quiet/grain/total-flat strengths.

The completed [V165 pair-common trial](pair-common-error.md) lowers native512 full-flat RMS **1.35–1.91%** and quiet spatial RMS **6.22–8.69% versus V164**. Mesh response falls 49–50% to parent level, and quiet color bias rises 7.67–28.07%; real crossings remain weak. Retain the grain/total-flat option beside stronger V161/V164 detail and V158 quiet accuracy. Both 1k heads, four endpoints, 822 cases, 72 actual native figures and independent audits are complete; 221 CPU checks, 94 final Adam states, exact controls and all 2,000 recorded weighted loss totals pass.

## Current hypotheses and evidence

The completed [V144/V145 pilot](v144-v145-quality.md) tests local RAW attention
from V143 with a larger branch rate and matched continuation. At 1k it gives
faint ADC −.00813 dB, noisy-flat spatial RMS +1.11% and no clear new mesh/organic
detail. The [photographic supplement](spatial-photo-supplement.md) confirms
near-parent outputs on 128 observations from 16 sources. All primary/flat/photo
audits and 154 native-board views are complete. This does not resume or relabel
the unstarted V132 experiment. A subsequent
[fixed whole-patch probe](cross-phase-patch-return.md) also adds noise without
useful detail. Further matching work needs explicit rejection of unsupported
noisy patches; V120/V143 recommendations are unchanged.
The subsequent [noise-scaled collaborative probe](collaborative-detail.md)
leaves all 48 analytic flats unchanged but transfers new color blocks into the
building crop while missing weak mesh. Confidence in a source group is insufficient;
query support must also be checked. The completed
[V138 frozen-parent trial](v138-quality.md) gives faint ADC +.00406 dB and noisy-flat
spatial RMS −.15% against V120, with no clear new mesh recovery. The original
1k run, all 150 review inputs, audits and 46 native-board views are complete.

| Question | Evidence and current action |
| --- | --- |
| Can targeted input response help weak-detail learning? | [Graikos et al., September 2026](https://arxiv.org/html/2609.36210v1) study perturbation regularization of generative denoiser Jacobians. Their ImageNet latent-generation results do not establish RAW fidelity or flat safety. Our inference is to test known signal response separately from noise response;the coupled sensor construction predates this reading. No external code/weights or paper reproduction adopted;V159 recipe fixed. [Primary-source record](results/paired-response-research-20261107-v1.json) |
| Can matched signal perturbations teach weak response more directly? | [Completed V160](paired-response.md): pair supervision raises mesh response 82–96% versus V143 to 4.00–4.31% of exact GT, with blank RMS +3.25–4.69% and quiet RMS +8.46–11.36%. Existing real strands gain slight contrast; crossings stay soft and fine colored grain rises. Ordinary new-data control improves native512 full flat RMS 0.42–0.53%, with a smaller quiet cost. Both heads/four endpoints/822 cases/72 actual native views and audits complete;123 CPU checks,450 frozen-base gradients and90 final Adam states pass. Original counter failure and23-batch adoption preserved. Retain the stronger response prototype while learning better structure/noise discrimination |
| Does removing common-loss support gradients retain detail? | [Completed V166](common-support-routing.md): it reduces quiet RMS6.10–15.27% and DC color bias17.52–31.30% versus V165,but all256 candidate mean supports remain below1e-4 and mesh stays near parent. The four-call/eight-adjoint probe verifies removed local-support gradients and surviving direct spectral/RGB routes. Other losses and changing inputs still affect support;scalar means do not isolate the closing mechanism. Full-flat/coarse means worsen modestly. Preserve the quiet-color gain without treating the path as retained |
| Can stronger absolute pair-common supervision retain the response gain? | [Completed V165](pair-common-error.md) reduces quiet spatial RMS6.22–8.69% and full-flat means1.35–1.91% versus V164, but halves mesh response and increases quiet DC bias7.67–28.07%. Candidate mean support becomes extremely small on all256 present-mesh cases while pre-support coefficient RMS rises. This suggests an optimization escape through support, without isolating causality. The common term is active on620 supervised batches; clipping rises205→454 of900. Independent2000 weighted-loss reconstructions and all72 actual native views pass. Preserve the grain/flat gain and investigate the delivered support path before adding further absolute pressure |
| Does the old paired-loss unit floor suppress weak-detail supervision? | [Completed V164](pair-unit-floor.md) lowers floor16→2DN16 at fixed V163 architecture/data/other losses. Actual metadata show620/1240 supervised pairs affected, including455/614 mesh. Response rises8.35–12.32% and all48 coarse flat errors improve at both endpoints; full-flat means and quiet spatial errors worsen. Real cab crossings remain incomplete. The physical Charbonnier transition also changes; global clipping prevents reading analytic unit ratios as actual update ratios. Independent1000-record unit audit, exact controls,199 CPU checks,94 Adam states and72 actual native figures complete. Preserve the response/coarse gain and false-detail cost; common pair errors remain invisible to difference loss |
| Does cross-frequency phase coupling recover weak detail at the V162 objective? | [Completed V163](harmonic-phase-inputs.md) adds16 bounded phase coordinates/512 parameters at fixed data/loss. Artificial-spectrum collision and adjoint tests establish representation semantics;actual trained-path displacement is only0.03–0.07DN16. Quiet mean bias falls2.60–3.96% and total quiet error0.62–1.19%,while mesh response falls0.52–0.59% and coarse-flat errors worsen on all48 cases at both endpoints. Real fine crossings remain soft. Preserve the small bias gain and the failure to recover detail;single-window noisy phase products are not calibrated confidence. All endpoints/822 cases/72 native views/audits complete,with failed disk guard and verified268-call adoption preserved |
| Can stronger absolute RGB targets curb common pair errors? | [Completed V162](flat-target-anchor.md) reduces quiet spatial error 4.73–7.73% on all 32 inputs and total-flat RMS 1.28–2.55% versus V161, at fixed architecture/data/base losses. Mesh response falls 20–22%; total quiet improvement is smaller, with six regressions and greater mean ISO12800 bias. Native views confirm grain reduction but soft crossings/broad casts remain. All four endpoints/822 cases/72 actual native views and audits complete; 156 CPU checks, 92 final Adam states, exact controls and 1,000 independent mask checks pass. Retain absolute target supervision as a grain-reduction option while preserving stronger response and addressing color bias |
| Can distant harmonic evidence reduce false grain while retaining response? | [Completed V161](harmonic-frequency-context.md) gains20.56–21.57% learned mesh response over exact V160 paired control, to 4.83–5.24% of GT,and all 48 coarse flat errors improve. Quiet RMS worsens 4.99–7.37%,with extra colored/gridded grain and bias;real crossings remain soft despite modest strand contrast. All four endpoints/822 cases/72 actual native views and audits complete;fixed 48-call context removal confirms active output changes in structure,blanks,flats and sky,without establishing accuracy or isolated training causality. 139 CPU checks, 91 final Adam states and exact 1000-row/control-state/1644 replay checks pass. Retain context/capacity gain while addressing flat-field costs |
| Does an invertible residual transform preserve the actual denoiser input? | [Poisson2Gaussian, June 2026](https://arxiv.org/html/2606.23098v1), sections3–5, read. Our inference distinguishes its augmented tuple from the collapsed input; [two exact algebra fixtures](results/poisson2gaussian-reading-20261107-v1.json) show why that distinction matters. No implementation adopted; V160 stays fixed |
| Can smoother small-regret pressure retain useful correction? | [Completed V159](regional-dc-transition.md): transition1e-4→1,weight1 fixed,reduces clipping726→101/882 and recovers modest coarse correction. Native512 full RMS −0.27–0.39%,block32 −0.17–0.19% versus V143;all 48 coarse inputs improve against V143/V158/V156 at both endpoints. Quiet total RMS rises0.18–0.48% despite lower spatial error;larger bias and weaker mesh response than V158,no new real crossings. Full four-endpoint/822-case/72 actual native review and audits complete,60 tests and exact V158 control states/replays. Preserve the coarse/quiet compromise;transition smoothing alone does not solve weak-detail recovery |
| Can explicit regional color-bias regret retain the coarse gain without quiet casts? | [Completed V158](regional-dc-regret.md): weight 1 RGB mean-error regret on unchanged hybrid removes the large V157 quiet color-bias increase. EMA quiet RMS −0.09–0.12% versus V143 on all 32 inputs, averaging −0.13–0.17% versus V156 EMA. Most coarse gain is lost: native512 full −0.046–0.053%, block32 about −0.001%; mesh still weaker than V143/V156, real crossings missing. All four endpoints/822 cases/72 actual native views and independent audits complete; 56 tests and exact V157 state/output controls. Clipping rises to 726/882 supervised batches versus 67/882; strong DC pressure/shared clipping as the cause of near-parent correction remains a hypothesis. Preserve useful quiet supervision while balancing detail/coarse learning |
| Can a spatial RGB path remove parent mottle while learning weak detail? | [Completed V157](spatial-rgb-residual.md): direct multiscale RGB path lowers native512 full/coarse noisy-flat error on all 48 inputs at both endpoints, versus V143/V156. Mean full gain 0.94–1.10% versus V143. Mixed quiet total RMS instead rises 10.26–14.98%; original-pixel decomposition identifies larger regional color/DC bias while spatial error falls. Mesh response drops below V143 and real crossings remain missing. Four endpoints/822 cases/72 actual views/audits complete; 45 tests and exact control states/replays. Retain the coarse architecture strength; next isolate local DC pressure and path coupling rather than claiming the whole hybrid solves weak detail and clean fields |
| Can local error control protect quiet neighbors while learning weak detail? | [Completed V156](local-excess-risk.md): weight 1 local32px RGB RMS-regret improves all 32 mixed quiet inputs versus matched MSE at both endpoints, mean0.30–0.63%; parent-level excess shrinks71–98% but many cases still regress. Response retains5.59–10.52% gain over V143; less than MSE, but1.76–3.07% higher than quieter V151 with lower mean quiet RMS. All four endpoints/822 cases/72 native views/audits complete; 36 objective tests/control states/1644 array replays exact. This improves allocation, not visible cab recovery or clean fields. Keep local loss for a spatial/coarse prediction path; proposal/support means alone do not prove selective restoration |
| Does a cleaner parent remove the quiet/detail tradeoff? | [Completed V155](matched-parent-comparison.md): fresh V120 and V143 under one deterministic FP32 policy, 822 cases each. V120 coarse noisy-flat RMS improves 1.59–2.36% while total RMS worsens 2.31–5.11%. Quiet RMS improves 0.39–0.91% but ISO6400 quiet spatial error rises; ADC slope full/coarse error worsens 33.26/112.65%. No convincing new real cab wires or clean native field. All 1,644 outputs,64 native figures and independent audits complete. Neither old parent array is adopted after the initial exact-replay failure. Retain explicit parent strengths; next investigate local spatial/coarse control together with weak-detail supervision |
| Does quadratic delivered error underweight weak coefficients? | [Completed V154](robust-spectral-objective.md): stable Charbonnier .01/.003 gives weak band errors more relative gradient pressure. Native512 noisy-flat RMS improves 0.45–0.50% versus V143, with lower actual mesh-blank errors than matched RGB MSE, but weaker mesh/natural response and mixed quiet RMS 1.51–2.27% worse than V143. Average support opens while proposal energy falls; neither proves selective recovery. All six endpoints/822 cases/96 actual native figures and audits complete; exact MSE control reproduces all 1,644 V153 RGB arrays. Same .25 coefficient changes gradient strength, not equal-norm objectives. Next examine cleaner parent and local supervision; band-only reweighting cannot remove parent coarse mottle |
| Does the spectral term supervise the correction that reaches the image? | [Completed V153](delivered-spectral-objective.md): delivered mosaic/RGB spectral loss raises mesh response6.04–7.97% over matched pre-support control, reaching2.45–2.59% of GT. Actual blank errors and natural-band attenuation worsen; ADC photo gains are lost. Quiet results are mixed, and mosaic coarse slope error improves with a DC tradeoff. No convincing new real crossings/organic texture. All three1k heads/six endpoints/822 cases/84 native views/audits complete; all1,644 control arrays reproduce V152 exactly. Stronger response prototype,not a broad solution. Next compare smooth robust delivered penalties for weak errors; RGB scales remain training proxies. Preclaim12-vs13 reviewer assertion/failure artifacts and corrected revision are preserved; training never restarted |
| Is the updated proposal or support responsible for V152's quiet regression? | [Completed fixed-map crossover](support-crossover.md): averaging both swap orders accounts for about79%/71% of added quiet MSE through the proposal change. RN retains small mesh/flat gains but worse quiet/natural response than NN. Full support now raises mesh response16.17–17.91% over V143, reaching2.56–2.60% of GT with worse actual blank/quiet errors; no convincing new real crossings. All six compositions/822 cases/84 native views and independent scalar/reconstruction/risk audits complete;1,644 original arrays replay exactly. Maps remain fixed, not recomputed on alternate proposals; no unique training/gate-weight causality. Next test spectral supervision after support/demosaicing; no new training or inference default |
| Does RAW/residual relative phase improve frequency estimation? | [Completed V152](relative-phase-estimator.md): response rises 1.27–1.41% over V151 noisy-only, with slightly lower noisy-flat and actual mesh-blank errors. Quiet regions worsen more, natural-band response drops further and native real wires/organic texture remain missing. All four endpoints / 822 cases / 72 native views/audits complete; 1,644 control arrays exactly replay V151. Input evidence and 2,304 parameters change together. Preserve the new feature for further estimator/support work, with V151's quieter behavior and V150's ADC gains retained; higher mean support does not establish selectivity |
| Can isolated noisy supervision recover the missing structure? | [Completed V151](noisy-objective-training.md): noisy-only improves mesh response 3.76–7.22% over V143 and native512 noisy-flat RMS .10–.16%, while exact quiet errors still rise and native cab wires/organic texture remain missing. Absolute response stays 2.28–2.36% of GT. ADC photo improvement shrinks from V150's3.06% to .22%. Peak8 nearly closes support, with no useful noisy recovery. All six endpoints/822 cases/84 native views/audits complete; all 1,644 control predictions exactly match V150. Noisy-only/16 DN/no peak becomes the next noisy-training control; stronger ADC and spatial routing remain open |
| Does noise normalization allocate pressure to the requested noisy detail? | [Completed diagnostic](spectral-loss-allocation.md) motivates [V150's completed matched2/16 DN trial](objective-floor-training.md). ADC clipping falls35→4 and actual noisy512 flat RMS improves .045–.047% versus V143. ADC photo full RMS improves3.06%, with band/coarse-slope tradeoffs. Weak mesh response remains4.3–4.5% below V143 and native wires stay missing. All4 endpoints/822 cases/72 actual native views/audits complete.16 DN is the next noise-focused training control; further ADC isolation and estimator evidence remain open, since ADC still supplies95.16% of a clipped-norm proxy |
| Can phase combination improve the late frequency estimator? | [Completed V148 matched comparison](phase-matrix-detail.md): complex4×4 mixing at1k lowers mesh response8–9% and raises native512 noisy-flat error .13–.24% versus V143. Strong-edge whole-image RMS improves .35–.47% while exact quiet patches worsen. Native256 ISO12800 RMS improves .06–.07%, without transfer to512. Four fixed endpoints, all58 native figures and independent audits complete; fresh scalar raw/EMA weights and all1,596 predictions exactly reproduce V147 |
| Does the spectral norm budget prevent missing-detail recovery? | [GT-informed capacity diagnostic](spectral-capacity-oracle.md): independently chosen bounded matrices raise mesh response .020→.717 using exact targets; frozen support limits it to .133. This relaxes the shared neural parameterization and does not establish input-only recoverability. Full-support GT witnesses create a false lattice in an exact quiet patch beside stripes. Larger corrections can also lower actual blank error, so change energy alone is not a hallucination measure. All792 cases/48 native figures complete; next work targets input evidence and spatial support |
| Can explicit CFA transport simplify useful evidence? | [Completed V149 matched1k trial](coherent-phase-estimator.md): known R/Gsum/Gdiff/B alignment raises mesh response2–3% over the native matrix control, yet the new arms remain6–7% below V143. Nine green-context features do not improve alignment's response and worsen blank errors. Strong-edge whole RMS improves .45–.74% versus V143 while exact quiet and native512 noisy-flat errors rise. All6 endpoints/798 cases/66 native figures and independent audits complete; native control reproduces all1,596 V148 predictions exactly. Next investigate supervision/gradient allocation; a loss imbalance is not yet established |
| Can a learned RAW innovation reach the output without another denoiser pass? | [Completed V1471k](late-spectral-detail.md): direct soft spectral correction after frozen V143 lowers mesh response about 8% and slightly worsens noisy flats. Small strong-edge image gains coexist with quiet-region regressions. Both fixed endpoints and 64 native figures are complete. Its 766-case raw-endpoint full-support intervention lowers response further to .00870 and adds false fine texture. The [updated V152 proposals](support-crossover.md) instead gain response at full support, with blank/quiet costs; the old intervention does not determine the newer baseline |
| Can a frozen foundation encoder supply useful detail supervision? | [Completed V128 pilot](v128-feature-pilot-quality.md): the26-call gradient diagnostic passes, but weight.1 gives no useful gain at1,000 matched updates. Independent scores and all28 native boards are complete; the term stays off by default |
| Can RAW phase/frequency features preserve thin structures? | [Completed V122/V123 trial](v122-v123-quality.md): V122 slightly improves weak eight-pixel carrier response; V123 gains0.05493dB photo PSNR against it but lowers unseen-camera PSNR and greatly worsens the ADC tail. Weak natural detail/mesh remain soft; full numerical/selected native review is published |
| Can local attention use spatial repetition more effectively? | [Completed V144/V145 1k](v144-v145-quality.md): ordinary +.00036 dB but faint ADC −.00813 dB and noisy-flat spatial RMS +1.11% versus matched continuation. No clear new mesh/organic detail across 154 native boards. The older [V131/V132 trial](raw-spatial-training.md) remains distinct: V131 stopped at 14,549 and V132 production never started |
| Can whole-tile matching preserve repeated weak detail? | [Completed normalized V1371k](v137-global-conditioned-quality.md) gives faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and no clear new lattice recovery. [Actual trained-memory removal](global-memory-contribution.md) changes0.83–1.39% of branch-offset RMS on six contexts; the local feature path dominates there despite varied attention. This is not a measured final-RGB effect |
| Can a larger update to the new branch help without moving the trained parent? | [Completed V138 1k](v138-quality.md): faint ADC +.02103 dB versus V137 but only +.00406 dB versus V120, noisy-flat spatial RMS −.15% versus V120, no clear new real mesh recovery. All 91 parent model/EMA tensors stay exact, 18 branch tensors train at LR1e−3, all 1,000 inputs match V137. Full 150-input/audit/native review is complete; combined scope/LR intervention |
| Can larger Fourier support and much more mesh supervision help? | [V146 at 500 updates](v146-coherent-frequency.md): packed128/native256 frames, LR .001, 1,246 present/1,183 empty meshes, frozen V143 parent. Raw/EMA mesh response+.62%/+.44%, image error+.051%/+.059%, all four photo groups regress slightly. Small flat/sky gains; no clear new native mesh. Both 694-input reviews and 22 native figures complete. Combined context/data/LR feasibility trial |
| Does inference geometry alone hide a useful larger-context gain? | [Completed V146 window transfer](v146-window-transfer.md): every learned tensor fixed, packed128→256/native256→512 support. Mesh errors grow .0017%/.0028% EMA/raw, response falls slightly; fresh512 noisy-flat errors also grow. 32 native figures and 72 fresh512 fields audited. The 112 short-context bypasses per endpoint are explicit; organic384 identity is not larger-window evidence |
| Can global matching learn without the local shortcut? | [V139 memory-only branch](raw-global-memory-only.md) retains15 tensors/14,144 parameters and a frozen V120 parent. Genuine CPU/CUDA16+2 checks pass. Original1k training and matched102-input native/faint/GFX review remain prepared after the dependency queue exited;510 predictions are reusable. Trained quality remains unmeasured |
| Can local arrangements improve memory matching? | [Completed standalone V140](v140-standalone-pilot.md) stays near V120 at1k, with no new mesh recovery and near-parent flat/sky variation. The original dependency queue exited. Its [branch diagnostic](results/v140-memory-amplitude-v1.json) measures memory returns at.97–1.60% of combined token RMS on six contexts; this is not an RGB quality measurement |
| Does stronger supervision of small gradient errors help? | [V141](v141-gradient-epsilon-pilot.md) isolates gradient epsilon3e−5 versus V1293e−4. Faint ADC+.01528dB, mixed local detail, no mesh recovery; noisy-flat coarse error near V129 and5.75% above V120. Defaults remain unchanged |
| Can explicit thin lines and absence improve the data prior? | [Completed V142](v142-crossed-line-pilot.md): faint ADC+.05212dB and noisy-flat spatial RMS−4.55% over V129. Selected grass/wood gain/error improve; fur is mixed and real mesh lacks clear new recovery. Coarse noisy error remains5.08% above V120; selected ADC-only DC bias worsens. Keep the useful data source for further trials |
| Can more learning combine the useful data and smaller-gradient changes? | [V143 fresh5k](v143-crossed-gradient5000.md) keeps V142 mesh/empty data with gradient epsilon3e−5. [Completed5k](v143-final5000-quality.md): faint ADC+.26493dB, noisy-flat spatial RMS−4.64%, coarse error+2.63% and ADC-only spatial RMS+12.85% versus V120. No clear new real-mesh lattice. Combined horizon/loss/data intervention, not equal-budget causality |
| Does training precision limit faint detail? | [Completed V130](training-precision-pilot.md) changes only BF16→FP32 training against saved V129. Selected weak fur/grass/wood [faint-ADC bands](faint-adc-precision.md) improve slightly in gain/error while global PSNR falls0.01720dB. Native changes are subtle; noisy material and real mesh remain weak |
| Is weak detail lost through persistent conditional bias? | [Independent-noise diagnosis](conditional-noise-response.md) finds persistent faint fur/wood error. [V12420k native check](v124-final20000-native.md) gains.411dB faint PSNR from14k but remains.0856dB below V120; ordinary gains.0095dB and real mesh stays weak. [V1256k](v125-progress6000-quality.md) remains1.009dB below V120 on faint contexts. Unequal budgets/backends prevent a causal mean-loss conclusion; full matched review remains incomplete after the memory-reserve stop |
| Does adding more realistic reviewed shadow detail help? | [Completed V126/V1271000-update pilot](reviewed-shadow-pilot-quality.md) finds no useful gain on its retained material/shadow/GFX support. Shadow policy stays off by default; the23-region reviewed bank remains available |
| Does fine-detail loss reweighting suffice? | [Completed V117/V11820k comparison](v117-v118-quality.md) finds lower weak natural-detail response and a worse ADC color tail with the normalized band term. Keep it off; improved local output-gradient alignment did not predict trained quality |
| Does encoder size alone fix weak contrast? | [Full Tiny/Small diagnosis](local-material-detail.md) finds nearly unchanged weakest-stratum gain on427 photos. Small's camera/detail tradeoffs remain useful; no size-only explanation is established |
| How much of the bigger corpus does a run visit? | [Full20k source audit](training-source-schedule-coverage.md) finds46.36% visitation at the spatial trial's50% reviewed quota versus69.26% at5%. [V133](reviewed-quota-training.md) retains that quota-only20k recipe against V131 after its original dependency queue exited; CPU/CUDA16+2 and independent saved-state checks pass. Quality remains unmeasured |

The latest [source inspection](v125-v131-source-review-5600-9800.md) brings the
ledger to 2,083 unique reviewed IDs and prepares 90,773 photos/37 regions. It
withholds one grainy coastal source and adds mixed leaf detail, preserving all
36 prior region objects. The actual reader visits all 37 regions; a saved
contrast-attenuated leaf sample has 254/256 eligible blocks below 5%, including
quiet areas. Strong grey plumage, mostly smooth stone and snow/sky annotations
remain ordinary photos; low contrast alone does not establish useful fine detail.
Quality work uses zero optical PSF augmentation and
geometry before final downsampling, with reviewed material regions and corrected
paired-reference masks. [Training pipeline](training-pipeline.md) ·
[Actual target contrast coverage](training-target-contrast-coverage.md).
The optional [photographic epoch order](photographic-epoch-order.md) addresses
replacement-sampling omissions: actual reader paths confirm full prepared-corpus
visitation within20k, with unchanged family/domain choices. This is a data
coverage result; its trained reconstruction quality remains unmeasured.
The matched [V134/V135 training comparison](photo-epoch-training.md) now has all
four real CPU/CUDA16+2 checks complete and retains20k recipes per arm on90778/33;
production/review are unstarted after the original dependency queues exited.
The [second V124 forty-source review](v124-second-source-review.md) retains38 and
withholds two display/artwork-dominated frames from a future90,778-source/33-region
cohort. It adds fine wing mesh and subtle pitted stone while preserving all31
prior region objects. Native annotations and actual saved full-context reader
draws distinguish intrinsic source contrast from augmentation. Existing training
inputs stay fixed: V131/V132 use90,781/29, with V131 stopped at the memory reserve and V132 unstarted;
[V1311k progress](v131-progress1000-quality.md) is mixed and full-endpoint/branch
quality remains unmeasured. The completed [V129](reviewed-detail-training-pilot.md)
27-region pilot has small mixed changes without clear large visible recovery.
The [new texture review](repetitive-material-source-review.md) adds one qualified
pale-feather context, preserving all33 earlier regions and the same90778 manifest.
Net-shop alias/moire and the grass-feather proposal's stronger contrast prevent
their specialized weak-detail admission. Existing trials and order policies stay fixed.

## Foundation features and the new objective

The official [DINOv3 implementation](https://github.com/facebookresearch/dinov3)
and [ConvNeXt-Small weights](https://huggingface.co/facebook/dinov3-convnext-small-pretrain-lvd1689m)
are locally available and hash-verified. Current recipes pin revision
`421020015aa4266363db803b6049a529999afb1e`, encoder SHA256
`691963f0f796aac860d818d59d9d14287a4675612829fbe9467c7f5df8ce5b14`.
The [pyramid implementation](dino-convnext-pyramid.md) supplies frozen spatial
context alongside the direct restoration path; pretrained feature access is
working. The existing [DINOv3 license](../third_party/dinov3/LICENSE.md) applies.

The recent [GramSR paper](https://arxiv.org/abs/2604.25457) motivates testing
DINO feature supervision. Our [early spatial-MSE experiment](dino-feature-supervision.md)
uses corresponding feature locations, native camera-RGB rendering and the
existing frozen encoder instance. Its diagnostic and pilot distinguish measured
output gradients from trained quality; no GramSR reproduction is claimed.

Two additional2026 preprints were reviewed on2026-11-03.
[Structural Guidance for Unified Joint Demosaicing and Denoising](https://arxiv.org/html/2608.09995v1)
combines frozen DINOv3 ViT-S/16,
CFA/noise-conditioned SwinIR,feature adaptation/residual fusion and an auxiliary
mosaic head. Its stated decoded-sRGB/Gaussian/fixed-RGGB scope and224px structural
input differ from our sensor-linear conditions. The listed GitHub URL returned404
during this check; release/license availability was not assumed.
[PixIE](https://arxiv.org/html/2605.23531v1) studies cross-scale denoising with
multidepth DINOv3 features and spatially continuous per-pixel modulation,using
neighborhood-aware embedding and compact attention. It is a low-light enhancement
study rather than our validated16-bit JDD comparison. Our inference is that
native-grid structural fusion deserves further controlled work; no source,
weights,data or reported gains were adopted into the running trial.

The current catalogue corrects an earlier title mix-up:2608.09995 is the
structural-guidance paper above. [SegDem](https://arxiv.org/abs/2608.07916) is a
separate August2026 preprint whose abstract describes segmentation-to-demosaicing
decoder transfer with a shared frozen DINOv2 representation. The initial correction
checked its abstract; a later method review is recorded below. Historical receipts and the cached2608.09995 HTML retain
their original bytes; this title correction changes no experiment or training
decision. [Exact correction record](results/structural-paper-title-correction-20261107-v1.json).

The [SegDem follow-up](results/segdem-followup-reading-20261107-v1.json) reads
its method and implementation appendices. Decoder-weight transfer and masked
spatial target-token alignment provide training supervision; the structural
encoder is removed for inference. Its synthetic/re-mosaicked Gaussian-noise
scope leaves native-camera generalization open. Our inference is to distinguish
decoder-feature supervision from output perceptual losses and online encoder
conditioning. Any later transfer still requires native fence and exact-flat
controls. The author repository returned404 through the connected GitHub tool;
no implementation, weights or data are adopted, and V166 remains unchanged.

The heldout review includes the main DSCF3879/3880 platform scene and the
additional DSCF3842 ISO6400 / **DSCF3835 ISO100 f/5.6** fine green mesh, with
camera JPEGs and independent low-noise references accurately labeled.
These private captures and siblings remain outside training.
[GFX comparisons](gfx-qualitative.md) · [Additional mesh](gfx-green-mesh.md).

## Comparator and implementation references

[RawNIND](rawnind-variants.md) remains an important released comparator;
its stronger variant still wins four of nine measured camera scene means.
The [nonlocal match/filter full review](nonlocal-reference-full-review.md)
and [other published-reference probes](experiment-archive.md) retain their
original finite support, source/license checks and input-transfer limitations.
They do not establish a universal ranking. Historical availability observations
are dated observations, not claims about today's upstream releases.

The [linear DNG/JPEG pipeline](dng-export.md) and hot-pixel repair are merged.
Complete102MP RGB16 output is verified; the100MP/10s target remains open.
Quality takes priority over optimization. [Current requirements](requirements.md).

The previous chronological design/access/release catalogue is preserved exactly
in the [timestamped diary](../diary/2026-10-27-00-42-21-dino-feature-supervision.md#exact-previous-research-page),
with its file hash and an independent byte copy. Frozen plans and original
machine receipts retain their bytes and explicitly labeled UTC times.

Earlier training and feature comparisons include [conditional-mean loss](conditional-mean-training.md),
[spatial attention](raw-spatial-training.md), [global RAW attention](v136-global-attention-quality.md)
and [neighboring-gradient memory](raw-patch-memory.md). Their original evidence remains available.

## Frequency separation and delivered flat behavior

[October 2026 RIECR](https://arxiv.org/html/2610.28191v1) separates exposure
estimation and residual restoration, with gated low/high convolution responses.
Its packed-RAW exposure benchmark does not establish our joint RGB quality.
No implementation or weights are adopted.

Our independent scalar fixtures show why frequency separation alone cannot
establish flat safety: an exact zero-DC kernel can amplify white-noise variance
by9/8, and nonnegative spatial gating after filtering can introduce DC. Zero
whole-image mean also permits local quiet-region shifts. The current spectral
proposal is spatially gated after its band restriction; future changes must
check delivered camera RGB, local bias and noise. These are algebra
counterexamples, not trained-model performance or a rejection of RIECR.
[Exact fixture/source evidence](results/frequency-gating-reading-20261107-v1.json).
V165's recipe was held fixed; its [completed comparison](pair-common-error.md)
records lower grain and total-flat error alongside lost mesh response and higher quiet bias.

The fixed [cab-band diagnostic](results/mesh-band-coverage-20261107-v1.json)
checks both native windows in cached ISO100 JPEG and independent AHD references.
Both dominant diagonal families fall inside the full nominal spectral band,
at packed radial frequencies0.213–0.281; some higher harmonics fall outside.
This weakens a cutoff-only explanation for missing fundamentals. The analysis
is a nominal mapping, not a learned transfer measurement, and the real
references remain qualitative rather than exact GT. V165 was unchanged.

The subsequent [retained training-coverage audit](results/mesh-training-coverage-20261107-v1.json)
reconstructs both clean sensor fingerprints for all 341 cached mesh batches
(682 pairs). Among 614 noisy pairs, 202 of 1,228 carrier families have center
periods inside the real reference's dominant 7.12–9.40 pixel interval, but only
13 pairs have both families there. The generator spans nominal 6–32 pixel
periods; projective geometry broadens the observed local period range. The
audit accounts for its Jacobian at five locations rather than treating the
nominal recipe as the final frequency. These are analytic carrier estimates,
not measured peaks after masking, interpolation and area reduction.

The noisy pairs' actual clean sensor difference has median RMS 2.48 DN16
(10th–90th percentiles 0.374–15.66); 264/614 are below 2 DN16 RMS and 47/614
even have peak differences below 2 DN16. Median full-context signal/input-noise
RMS ratio is 0.00932. That energy proxy does not measure matched-filter
detectability or restored RGB error. The 68 ADC-only pairs are reported
separately. This suggests testing stronger coverage of fine crossed carriers
across an explicit contrast/noise ladder, with matched empty controls. Simply
lowering contrast would make many already weak examples weaker. This is a
data hypothesis, not an established explanation or quality gain; V167 remains
fixed. No new training pixels, sensor draws, neural forwards or original media
reads were used for this audit.

The [completed V168 experiment](fine-mesh-training.md) implements that data test with
171 changed mesh batches and 829 legacy batches. Actual changed noisy-pair
signal RMS has median 10.71 DN16 versus 2.32 before; masks and clean empty
backgrounds are independently checked. It changes frequency and contrast
coverage jointly. Matched V167 control trace,state and1,644 actual predictions
reproduce exactly. Mesh response rises17.48–18.09%,to3.805–3.836% of GT; the nine
both-fine recipes gain about59%,still only1.8% of GT. All48 coarse-flat errors
improve at both endpoints. Quiet RMS rises1.49–5.44%,all32 quiet spatial errors
worsen,and total-flat means rise0.136–0.228%; fine real crossings remain
incomplete. The data result is useful but does not resolve the quiet/detail
tradeoff or isolate frequency from contrast. All822 cases,four endpoints,
72 actually viewed native figures and independent audits are complete. Original
resource/policy stops,750-state recovery and2770-forward review adoption remain
preserved; no full-training restart or repeated review inference.

## Native frequencies from packed phases

[DFENet](https://arxiv.org/html/2503.15800v1), with a November2026 journal issue
and March2025 preprint, separates spatial detail refinement from CFA-guided
frequency suppression. Sections3–5 describe staged RGB/spectral supervision,
Gaussian CFA-noise tests, synthetic line patterns and local patch inference.
Those results do not establish physical shot/read-noise behavior or our sky/fence
quality. No paper implementation, weights or dataset are adopted.

Our eight deterministic scalar-mosaic fixtures distinguish invertible packing
from averaging. All four phase spectra, combined with their native phase factors,
reconstruct every full-resolution mosaic Fourier bin: maximum difference
4.33e−17 versus FFT and 5.93e−16 versus an independent dense DFT. Pack/unpack
is bit-exact. Two native frequencies, +0.125 and −0.375 cycles/pixel, have identical
even-x phase samples and matching per-phase spectral magnitudes after DC removal,
but different cross-phase signs. The complete packed tuple distinguishes them.

Our inference is that explicit native-alias features could make available phase
relationships easier to learn. Packing itself does not discard recorded RAW
samples; dropping phase, mixing phases or restricting bands can discard distinctions.
This algebra does not reconstruct unmeasured RGB samples, measure trained detail
recovery or establish flat safety. V166's fixed common-support routing trial is
unchanged. [Own fixtures, source and primary-paper record](results/packed-fourier-reading-20261107-v1.json).

## Inspecting a recent wavelet objective

The July2026 [WGCAN publisher abstract](https://www.sciencedirect.com/science/article/pii/S0262885626002441)
describes wavelet low/high processing followed by color reconstruction. The full
publisher page returned403; the abstract and author code were reviewed separately.
At [pinned author commit87413dd](https://github.com/user-hbj/WGCAN/tree/87413dd280af8228f34fe33188136077ad81ca68),
the wavelet term sums mean L1 differences over all four one-level Haar bands,
including LL. Training uses RAW/RGB/wavelet weights0.7/0.2/0.1 after RGB clipping;
the reported validation loss uses0.5/0.4/0.1. A helper's Euclidean name does not
describe its actual L1 operation.

Our inference is to specify the exact transform, normalization and subband
weighting before interpreting any wavelet-loss comparison. This paired-exposure
RAW/RGB pipeline does not establish our physical-noise-conditioned camera-RGB
or quiet-sky quality. The inspected repository declares no license; no code,
weights or data are adopted. V166 remains fixed. [Primary URLs, pinned file hashes,
line references and reading limits](results/wgcan-reading-20261107-v1.json).
