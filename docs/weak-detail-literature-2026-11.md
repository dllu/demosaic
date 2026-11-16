# Recovering weak detail without inventing texture

Literature and project review, **2026-11-15, America/Los_Angeles**.
This is a research note: proposals below are unimplemented and unmeasured.

Implementation follow-up, November 16: the first shared-edge trial is
[finished training and matched native review](shared-edge-comparison.md), and the
[first analytic withheld-CFA/edge diagnostic](withheld-cfa-evidence.md) has
completed, followed by a [geometry-refinement comparison](withheld-cfa-edge-refinement.md).
The [fresh-noise neural finite-wire panel](edge-snr-ladder.md) completes all three
noise profiles; weaker response remains low even when strong response improves.
The [competing-orientation model trial](competing-orientation-comparison.md) has
finished matched training and raw/EMA/native evaluation: one fixed mesh improves
its weaker orientation, with lower overall mesh response and persistent artifacts.
Its [complete fresh-noise follow-up](competing-edge-response.md) finds higher
far-edge weak response with strong-direction losses and mixed quiet effects.
The [complementary-stage follow-up](complementary-cfa-branch.md) has trained above
frozen V200 EMA with extra proposals; its [full native review](complementary-comparison.md)
finds almost unchanged weaker directions and slightly higher quiet/flat error.
Its [complete fresh-noise review](complementary-edge-response.md) finds a small
lower-noise weak-response gain with mean strong response retained. The
[coverage-to-response follow-up](complementary-coverage-quality.md) verifies all
closed carrier choices on CUDA and finds substantial attenuation among close-
carrier views; global proximity alone is not a reconstruction bound.
The [existing full-model RAW-attention comparison](raw-spatial-continuation.md)
completes its original20k control: [V131 targeted quality](v131-endpoint-quality.md)
has faint-ADC +0.14555 dB across four sources with a bark regression, small
ordinary/shadow gains and no convincing new real mesh crossings. V132's
added-attention arm is training, with original source and20k horizons preserved.
Its [matched1k/native review](v132-progress1000-quality.md) finds faint-ADC
+0.03356 dB versus V1311k but−0.23979 dB versus V120, without clear new real
crossings or foliage recovery. That early gain does not establish convergence.
The proposals below remain the original November 15
assessment; measured follow-ups are linked here rather than rewriting history.

**The next useful step is better discrimination between weak structure and
noise/edge leakage, coupled with training that rewards that distinction.**
The project has demonstrated real detail gains, but increasing response alone
has repeatedly increased false texture. I would first evaluate the prepared
shared-edge data intervention, then investigate genuinely withheld-sample
evidence and edge-aware local reconstruction. A larger modern restoration
backbone remains a worthwhile comparison, but it would not by itself explain
or remove these failures.

## What the existing work establishes

| Evidence | Progress | What remains unresolved |
| --- | --- | --- |
| [V120 general model](v120-v121-primary.md) | 37.04008 dB on 427 photos, working DINOv3/DRUNet integration, verified 102MP RGB16 exports | Fine foliage, mesh, neon and dark-field mottle; broad SOTA and 100MP/10s remain unproven |
| [Repeated-noise diagnostic](conditional-noise-response.md) | Selected faint fur/wood errors persist across independent corruptions; selected bark errors are more variance dominated | This is evidence of attenuation as well as noise, not proof of its architectural cause |
| [Measured green phases](green-phase-spectrum.md) | Both greens contain coherent diagonal peaks where earlier outputs lose power | Phase agreement is not calibrated confidence; [real supported frequencies can also have negative cross-power](green-phase-reference.md) |
| [Known-template context diagnostic](mesh-template-evidence.md) | Median green template SNR rises from 0.653 at the best native16 window to 7.360 at native512 | Uses the hidden template/background; does not prove that unknown mesh can be located safely |
| [V187 → V195 → V198](scale-supported-cfa-wave-comparison.md) | Held-out constructed-mesh projected amplitude rises 5.359% → 5.575% → 11.158% of GT | V198 adds building color fringes and higher blank/quiet error; amplitude is not overall reconstruction quality |
| [V199 gate interventions](cfa-wave-gate-diagnostic.md) | Shared-color, constant and positive-only controls clarify the failure | Constant gates look cleaner partly because they greatly weaken corrections; artifacts return at matched correction RMS |
| [V200](scale-supported-cfa-wave-comparison.md) | Cross-scale support reduces quiet RMS 0.059–0.119% and fresh-flat RMS 0.022–0.030% versus V198 EMA | Response slips to 11.102%; fringes, flat ripples and incomplete crossings persist |
| [Shared-edge preparation](paired-training-coverage.md) and [consolidation](architecture.md) | Cache ready; repeatable experiment runner and retained composed models | Shared-edge model quality is unmeasured; engineering consolidation is not a quality gain |

The current data already contains reduced-contrast photos, procedural mesh,
paired signal increments and noisy flats. The specific audited gap was that
**all 139 noisy mixed edge/quiet batches had zero coupled pairs**. Suggesting
“add low-contrast augmentation” would miss that distinction. Previous local
attention, collaborative matching, dense spectra, larger support, phase
features, stronger response losses and stronger flat losses also have recorded
mixed or negative outcomes; [the research history](research.md) remains relevant.

I inspected the saved V200 EMA synthetic mesh2302/2309 triplets and the small
real cab/building triplets. The cab reveals one diagonal family much more
clearly than complete crossings; the building has conspicuous green/magenta
fringes near a strong structure. The synthetic examples show similar direction
imbalance and incomplete thin segments. These observations suggest testing
localization and competing structures, rather than treating extra Fourier
power as recovered fence.

Existing native100% evidence, with original pixels and provenance:
[mesh2302](images/v200-scale-supported-cfa-wave-v1/comparison-02.png),
[mesh2309](images/v200-scale-supported-cfa-wave-v1/comparison-06.png),
[cab](images/v200-scale-supported-cfa-wave-v1/readme-cab-v1.png),
[building](images/v200-scale-supported-cfa-wave-v1/readme-building-v1.png).
Synthetic cells are native160, ROI `[176,176,160,160]`, RGGB,
shot `0.00128`, read `6.5536e-6`, exposure8/contrast1.
V200 EMA export SHA256:
`2bb4a05943b6e9c1eb31877d19058ca4a3fea723666510fbaa133554d6ef7d22`.
[Manifest](images/v200-scale-supported-cfa-wave-v1/manifest-v1.json) and
[real-triplet provenance](results/v200-scale-supported-cfa-wave-v1/representative-figures-v1.json)
contain full source/ROI/noise/display bindings. Real ISO100/AHD references are
independent captures with different aperture/exposure/motion, **not exact GT**.
No new model performance report is implied by this review.

## What recent literature contributes

Search scope: primary papers and proceedings, emphasizing 2026 and late 2025,
with older statistical work where it directly addresses false detail.
“State of the art” below is benchmark-specific: RGB AWGN, RAW denoising,
self-supervised sRGB denoising and joint Bayer reconstruction are different
tasks. Their scores cannot be compared with our 427-photo score.

| Primary source and reading scope | Finding relevant here | Transfer limit / useful takeaway |
| --- | --- | --- |
| [NTIRE 2026 image denoising challenge](https://arxiv.org/html/2606.16031v1), June 2026; protocol, leaderboard and method overview | BuptMM leads at 29.90 dB on the fixed sigma50 RGB AWGN task. Leading entries combine modern convolution/attention/state-space components, large curated datasets, progressive crop sizes and inference ensembles. | No compute limit and no Bayer/physical-noise task. Worth a stronger supervised-backbone comparison and longer, larger-context training; the winning score is not evidence for safe low-amplitude RAW reconstruction. |
| [AIM 2025 real-world RAW denoising challenge](https://arxiv.org/html/2510.06601v1), October 2025; protocol and leading methods | MR-CAS leads overall/fidelity using a NAFNet variant, random masking and progressive training. The benchmark supplies calibrated gains and dark frames; authors emphasize noise synthesis and training strategy. | More directly relevant than RGB AWGN, but RAW-to-RAW rather than JDD. Separate fidelity and perceptual rankings; reuse ideas only after checking data/code licenses. |
| [Structural Guidance for Unified JDD](https://arxiv.org/html/2608.09995v1), August 2026 preprint; method, protocol and implementation appendix | CFA/noise-conditioned SwinIR, frozen DINOv3, residual feature adaptation and auxiliary clean-mosaic supervision. | Already reviewed here. Decoded-sRGB/Gaussian synthesis and 8-bit metric quantization differ from our task. Its documented no-gradient encoder call blocks learning of the preceding stem; copy the idea carefully, not the assumption that every nominal adapter learns. |
| [Learned Nonlocal Feature Matching and Filtering for RAW Image Denoising](https://arxiv.org/html/2604.17453v1), April 2026 preprint; method and RAW results | Learned matching, collaborative filtering and aggregation with noise maps. Reports DND sRGB PSNR 40.63 versus DualDn 40.70, with a different SSIM/visual tradeoff. | Competitive, not universally best; already an optional project comparator. Our failed whole-patch transfer shows that confident source patches are insufficient without query-local support. |
| [Next-Scale Prediction](https://arxiv.org/html/2512.21038v2), December 2025 / April 2026 revision, CVPR2026; method and experiments | Separates noise decorrelation from fine-scale prediction through disjoint cross-scale training samples; improves self-supervised SIDD performance and addresses shuffle artifacts. | RGB blind-spot benchmarks, not a proven Bayer recipe. Preserve actual CFA coordinates and test noise dependence; aggressive spatial subsampling can discard the very fence phase we want. |
| [IDF: Iterative Dynamic Filtering](https://arxiv.org/html/2508.19649v1), August 2025 / ICCV2025; method and normalization | A compact model predicts local kernels, applies the same kernels across RGB channels, and iterates. It studies generalization beyond its training noise. | A useful constrained-output alternative to free residual synthesis. A direct packed-RAW port would be wrong because the channels occupy different sensor sites. Its convergence-based “confidence” is not a calibrated false-detail probability. |
| [PixIE](https://arxiv.org/html/2605.23531v1), May 2026 preprint; method | Cross-scale denoising plus multidepth DINOv3 prompting, neighborhood embeddings and continuous pixel modulation. | Low-light enhancement rather than sensor-linear JDD. Motivates better native-detail/context fusion; does not justify a semantic prior choosing fence phase or inventing crossings. Already present in earlier project reading. |
| [Benchmarking RAW and RGB Restoration in ISPs](https://arxiv.org/html/2609.02831v1), September 2026 preprint; protocol, conclusions and limitations | Target-ISP-trained RGB models reverse the ranking against generic RGB models; training/pipeline alignment matters greatly. | Only 47 test images; comparisons are not fully training/loss matched. Supports checking training-domain mismatch, not abandoning RAW restoration. |

Three statistical references sharpen the proposed experiments.
[Noise2Self](https://proceedings.mlr.press/v97/batson19a.html) (ICML2019;
paper proposition and abstract) gives a clean reason to withhold the samples
used to assess a predictor: conditional noise independence and a predictor
that never sees the held-out coordinates make noisy validation informative.
It does not guarantee arbitrary masked networks or correlated camera noise.
[Automatically Adaptive Conformal Risk Control](https://proceedings.mlr.press/v258/blot25a.html)
(AISTATS2025; abstract) motivates measuring risk conditional on difficulty,
rather than accepting a good global average. Its guarantees require the actual
calibration procedure and assumptions; a learned support score is not enough.
[The Perception–Robustness Tradeoff](https://proceedings.mlr.press/v235/ohayon24a.html)
(ICML2024; abstract) warns that perceptual realism plus measurement consistency
does not automatically imply stability. It is not a theorem that our particular
fence is unrecoverable.

These readings support deterministic, measurement-grounded experiments first.
Diffusion/perceptual texture generation is a lower priority for this fidelity
goal. A plausible lattice, or a correction that survives re-mosaicking, can
still have the wrong phase, color or unmeasured-channel structure.

## Proposed experiments, in priority order

The following are **our hypotheses**, not demonstrated conclusions of the
cited papers. Each should retain matched controls and test a distinct question.

### 1. Finish the shared-edge data question before changing architecture

Use the already prepared intervention: both members contain the same strong
edge/background, while only one contains a faint mesh increment. Preserve
absolute-image and quiet-region supervision alongside the pair difference.
This asks whether the current estimator can learn to separate a weak increment
from a common strong scene, rather than merely distinguish texture from a
constant patch. Compare with the exact V200 replay recipe; document that scene
content and pairing change together, so a gain would not isolate one cause.

Then, if useful, add controlled families: zero/one/two wire directions, unequal
direction strengths, finite wires, occlusions, varying spacing/subpixel phase,
color contrast and edge distance. Include grass, fabric and feather-like
nonperiodic structures so “detail” does not become synonymous with a lattice.
Use generic training-only scenes and freely licensed photos, never the held-out
GFX pixels. Pair coupling reduces variance of the training comparison; it must
not be mistaken for independent sensor evidence. Evaluate with fresh marginal
noise draws and independent repeats as well.

**Decisive result:** more of the weak second direction at the same measured
blank/quiet error, including near strong edges. Merely stronger first-direction
modulation or lower average image error would not answer the question.

### 2. Separate discovering a candidate from validating its evidence

Current top-bin selection, amplitude fitting and cross-scale agreement reuse
the same RAW data. Even pure noise has a largest peak, and overlapping windows
can agree on it. Furthermore, `RAW - mosaic(parent(RAW))` contains correlated
parent errors. Dividing by RAW variance does not calibrate that innovation.

Prototype a diagnostic using disjoint, CFA-stratified sensor subsets A/B:
discover frequency/orientation/support and fit the candidate using A; ask
whether that fixed prediction reduces error on B compared with an A-only
background predictor. Reverse A/B and combine only under a prespecified rule.
Do not tune frequency, phase, gain, window or threshold on B and then call B
independent validation. Use native coordinate operators rather than resizing
one green plane onto another.

The important trap: an ordinary frozen V120/V195 output has seen **both**
subsets. Subtracting it before splitting leaks B into A. The baseline, proposal,
noise estimate and any DINO features used in this diagnostic must also exclude
B, or the result must be labeled empirical rather than independent. Start with
an analytic A-only nuisance fit; a masked neural baseline is a later experiment.
Splitting reduces SNR, so compare detection power with full-data methods rather
than assuming it will improve final images. Correlated row/read noise requires
appropriate blocks/covariance and may invalidate simple independence.

Calibrate the complete selection-and-validation procedure on fresh exact flats
and edge-only scenes, including the search over all candidates. Measure false
activation per patch/frame, not just per chosen coefficient. Formal risk control
would require a separate calibration set and its assumptions; first establish
an empirical detail-versus-false-texture curve. No universal threshold follows
from the current green coherence values.

If this evidence separates the classes, compare smooth shrinkage with a hard
gate: pool coherent measurements first, then attenuate the fitted amplitude
according to empirically calibrated support. A candidate Bayesian formulation
mixes an explicit no-detail model with one-/two-direction models and averages
their predictions. That can avoid an abrupt threshold erasing faint wires,
but a misspecified prior can still favor a false lattice. Learn/calibrate model
preferences on independent data; evaluate both missed-detail and false-detail
rates instead of treating posterior labels as guarantees.

### 3. Model strong edges as competitors, and localize synthesis

An affine background cannot explain a step edge. Its residual spectrum can
look like a family of plausible waves; this is a concrete explanation to test
for the building fringe, not an established cause. Compare a local sensor-domain
fit with a piecewise-smooth edge/background component and an optional weak
detail component. Joint fitting is preferable to blindly subtracting a smooth
image that may already remove the fence. In a fixed linear diagnostic,
project the candidate out of the nuisance basis using the noise-weighted inner
product; report when the remaining candidate becomes unidentifiable.

Choose geometry on A and validate on B as above, or calibrate the entire
data-dependent fit empirically. Add smooth finite support, edge stopping and
separate competing orientations; synthesize only where each component has
local evidence. A long wire can pool evidence along its direction without
copying a periodic ripple across a nearby flat surface. Perspective variation,
curves and occlusions must be allowed. Never force a second orientation merely
because the scene resembles a fence.

This extends the existing local affine fits and V200 scale agreement; simply
adding more window sizes would repeat earlier work. Excessively flexible
nuisance models can absorb true wire detail, while insufficiently flexible ones
leave edge leakage. Sweep that tradeoff on exact known targets before training.

### 4. Compare measurement aggregation with wave synthesis

Adapt the useful part of NLFeMF/IDF: infer where to aggregate, but reconstruct
from actual, phase-aligned measurements. Test local oriented kernels or small
collaborative groups with query-local validation, against the existing wave
head at matched quiet error. Permit multiple orientations and a no-match
fallback; nearest neighbors always exist even on noise.

For an exactly normalized nonnegative same-color kernel, a truly constant input
is preserved and a fixed kernel cannot create values outside its neighborhood
range. This is an algebraic property, **not** flat-safety on noisy input:
data-dependent weights can select noise, and averaging across a wire erases it.
Estimate geometry over broad context but aggregate along compatible phase and
support. In Bayer data, retain sensor offsets and separate color amplitudes;
do not impose identical RGB values or infer red/blue waves from green alone.
V199 already shows that shared RGB gains by themselves do not fix color errors.

### 5. Give coarse mottle and fine response distinct training routes

The existing history contains actual parameter-gradient conflict between
flat-spatial and paired-detail objectives. Reweighting either side has often
traded one problem for the other. Test separate coarse color/bias and detail
branches with explicit band/DC constraints and controlled gradient sharing.
Supervise coarse error at several spatial scales; supervise fine amplitude,
phase and both directions plus absent-detail error. Retain absolute targets:
pair differences alone miss common hallucinations.

This is a factorization experiment, not a first proposal for a spatial branch
or a spectral loss—V157, V153/V154 and later flat-loss studies already tried
those. A zero-DC detail branch cannot repair inherited broad mottle, and variable
spatial gates can reintroduce low-frequency energy. Check the **delivered
correction after gates and blending**, not just a pre-gate coefficient budget.
Do not remove the band containing the weak 27.69-pixel fundamental found in
[V196](innovation-frequency-selection.md) by defining “detail” too narrowly.

Independent-noise repetitions can diagnose signal attenuation versus output
variance, extending the existing conditional-response work to the new heads.
Evaluate phase/direction and off-target energy as well as template projection;
a high projection can coexist with rounded nodes, doubled wires or false color.

### 6. Check sensor and training-domain mismatch before adding confidence claims

The green-mesh nominal noise coefficients are a prior, and the alternate
DSCF3879 profile comes from another capture. Compare plausible shot/read
coefficients, black offsets, unequal green response and correlated row/column
noise using training/calibration data separate from both GFX test families.
Dark/flat calibration, if later available, would distinguish camera bias from
network mottle more directly than visually tuning a coefficient on the fence.
Mean shot-noise dominance does not exclude a small correlated component that
matters greatly when pooling hundreds of pixels.

Also test small, physically justified optical/pixel-integration variations
against the current zero-optical-blur recipe, as a separate ablation. Native
phase, pre-binning geometry and sharp fine targets must survive. Rendered and
8×-binned source photos are useful constructed targets but do not recreate
native RAW optics or remove every JPEG/ISP artifact. Do not simply blur all
training targets; that could teach more attenuation.

### 7. Revisit the backbone and DINO role after these discriminating tests

Use one modern supervised comparison—e.g. a NAFNet/Restormer-style native RAW
branch with the same data/noise/objectives and existing DINO context—rather
than assuming successive small frozen-head trials bound what a full model can
learn. The recent challenge results make larger-context training and curated
data coverage at least as credible as a new frequency module. Short 900-update
head studies establish their measured outcomes, not convergence of every design.

Let DINO help predict support, boundaries or compatible neighborhoods while
physical RAW evidence determines fine phase/amplitude. Compare that role with
current fusion; DINO feature-loss pressure has already had an unsuccessful
pilot here. Auxiliary **clean** mosaic supervision can be tested with careful
loss units. For noisy input, hard equality to observed mosaic values would
preserve noise, and re-mosaicking alone cannot validate unmeasured RGB channels.
Keep 16-bit-sensitive arithmetic and evaluate end-to-end memory/time later;
neither an AWGN leaderboard nor a tiny head parameter count establishes GB10
full-frame feasibility.

## What would make the next result convincing

The first small study should be the prepared shared-edge comparison. The next
diagnostic should test A/B-held-out evidence with and without an edge nuisance
model. Only then choose between localized waves, constrained aggregation or a
larger learned model based on where those diagnostics fail.

Report a curve of **weak-detail recovery versus actual false-detail error**,
not a single amplitude score. Use exact present/absent pairs, edge-only scenes,
flat gray/color fields, slow gradients and natural fine textures. Stratify by
SNR, frequency, direction, phase, distance from edges and CFA; report means and
bad tails. Include regional DC/chroma error and low-frequency mottle separately
from fine ripple error. Equal correction RMS is a useful diagnostic control,
but matching measured error in quiet regions answers the user's tradeoff more
directly. Use independent sources/noise seeds and source-level uncertainty;
adjacent Fourier bins and overlapping crops are not independent replications.

Keep both standing real-photo families: DSCF3879/3880 sky/building/foliage/
chain-link fence, and DSCF3842/3835 left/right cab mesh with both JPEGs and both
retained noise profiles. They and their siblings remain excluded from training.
These repeatedly reviewed scenes are development qualitative checks, not a new
blind test or pixelwise scoring target. Include new held-out scenes for any
generalization claim. Future improvement reports must retain at least two
native100% noisy/restored/exact-GT triplets, identical coordinates/transforms,
checkpoint hashes and noise/display metadata; label independent real references
accurately. Keep genuine gains and counterexamples visible together.

No architecture, loss, data recipe, checkpoint, inference setting or experiment
was changed or run for this note. Existing evidence and original media remain
unchanged.
