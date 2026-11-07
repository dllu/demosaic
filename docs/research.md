# Current method research

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
| Can matched signal perturbations teach weak response more directly? | [Coupled sensor-noise primitive](coupled-counterfactual-noise.md): common-minimum Poisson counts plus independent increments/shared read draw preserve each target's sensor marginal.16 tests and four retained physical-moment fixtures pass. This prepares data for a possible paired-response loss;no training or restoration gain yet. Coupled differences are not independent captures,and a response loss could increase noise sensitivity. V159 remains unchanged |
| Can smoother small-regret pressure retain useful correction? | [Completed V159](regional-dc-transition.md): transition1e-4→1,weight1 fixed,reduces clipping726→101/882 and recovers modest coarse correction. Native512 full RMS −0.27–0.39%,block32 −0.17–0.19% versus V143;all48 coarse inputs improve against V143/V158/V156 at both endpoints. Quiet total RMS rises0.18–0.48% despite lower spatial error;larger bias and weaker mesh response than V158,no new real crossings. Full four-endpoint/822-case/72 actual native review and audits complete,60 tests and exact V158 control states/replays. Preserve the coarse/quiet compromise;transition smoothing alone does not solve weak-detail recovery |
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
[SegDem](https://arxiv.org/html/2608.09995v1) combines frozen DINOv3 ViT-S/16,
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
