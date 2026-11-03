# Current method research

The [reciprocal green-support option](cross-phase-support.md) cuts fresh mean
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
highlight color, bounded-solver accuracy and speed remain open. `edge` is now the
optional-stage default; earlier `complex` and `scalar` modes remain available.

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

| Question | Evidence and current action |
| --- | --- |
| Can a frozen foundation encoder supply useful detail supervision? | [Completed V128 pilot](v128-feature-pilot-quality.md): the26-call gradient diagnostic passes, but weight.1 gives no useful gain at1,000 matched updates. Independent scores and all28 native boards are complete; the term stays off by default |
| Can RAW phase/frequency features preserve thin structures? | [Completed V122/V123 trial](v122-v123-quality.md): V122 slightly improves weak eight-pixel carrier response; V123 gains0.05493dB photo PSNR against it but lowers unseen-camera PSNR and greatly worsens the ADC tail. Weak natural detail/mesh remain soft; full numerical/selected native review is published |
| Can local attention use spatial repetition more effectively? | [Optional RAW spatial branch](raw-spatial-features.md) adds22,664 parameters and preserves constant features. [V131's unchanged-architecture control at1k](v131-progress1000-quality.md) has tiny ordinary gains, deeper-shadow/faint regressions, mixed local response and no clear new mesh recovery. V131 stopped at the memory reserve on90,781/29; V132's branch and full-endpoint quality remain unmeasured |
| Can whole-tile matching preserve repeated weak detail? | [Completed normalized V1371k](v137-global-conditioned-quality.md) gives faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and no clear new lattice recovery. [Actual trained-memory removal](global-memory-contribution.md) changes0.83–1.39% of branch-offset RMS on six contexts; the local feature path dominates there despite varied attention. This is not a measured final-RGB effect |
| Can a larger update to the new branch help without moving the trained parent? | [V138](raw-global-only-training.md) freezes91 parent model/EMA tensors and trains18 normalized global tensors at LR1e−3. Genuine CPU/CUDA16+2 checks pass; original1k production and native/GFX review remain unstarted after the V125 dependency queue exited. A bounded companion will compare trained-memory contribution with saved V137 after its reviews finish. Combined scope/LR intervention; quality remains unmeasured |
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
