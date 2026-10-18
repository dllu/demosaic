# Censored-highlight gradient counterexamples and completed primary photo panel

Previous goal turn classification: progress. Both V76/V77 first1k arms completed,
all camera stages and22 early native triplets/34 cells were reviewed, full CPU
suite passed1021/9 skips and interim source/pixel reports were pushed05a1ed1.
This turn makes progress with a new actual CPU representation/gradient audit,
not just waiting: production semantics/gates remain unchanged. Goal stays active;
SOTA, decisive real-photo superiority and100MP/10s remain unmet/unproven.

At turn entry actual full427 child3944292/1792347606.57 and CPU closure owner
3941383/1792347215.59 were verified live, not inferred from stale status files.
Full427 progressed27739->42577->50754->59199->61310->62020 rows, and exited
successfully before statistics/source-sensitivity/GFX/analytic. Source/weights
and current study/gates were not changed or restarted. At this snapshot review
status=running-camera-supervision-quality-review, stage=highlights, completed=['boundary', 'known', 'unseen', 'full427', 'statistics', 'sensitivity', 'gfx', 'analytic', 'hue'].

Primary panel now complete: V77-minus-V76 full427 renderedPSNR+.16010560dB,
source95% CI[+.09817897,+.23935610]; renderedSSIM+.0003378454,
CI[+.0002462858,+.0004564784]. Means36.10173560/.963587768 vs35.94163000/.963249922.
Unchanged canonical camera-linearPSNR loses2.13180530dB, CI[-2.23866146,-2.00332702];
this target differs from physical training, retain the score/caveat, no relabeling.
Procedural16 gains+.75338821dB renderedPSNR/+ .003268662 SSIM, but loses1.16475dB
canonical camera-linearPSNR. Keep these separate from the427 photographs.
Per-condition rendered means: ADC+.03937, ISO100+.31053, ISO1600+.23320,
ISO12800+.11011, shadows-.01673, highlights+.20485, original-noise+.23941dB.
These descriptive condition means do not have new condition-specific intervals.

Known camera-.02713908dB/unseen+.08098272dB remain unchanged and known fails the
original >=+.05dB/positive interval requirement. No extension/promotion despite
positive photographic/unseen results. Source sensitivities complete with an
independent Decimal/scalar audit of215208 metrics/7686 source scalars, source
difference0;81 comparisons/540 fields, max3.55e-15. Seventy-two early native
PNG/JSON/report refs rechecked after actual full427 producer exit; original PID
absence verified. Primary-progress.json binds all results, including per-condition
linear/sRGB/SSIM. Remaining hue/highlight/native/statistical closure still pending.

Actual completed GFX/analytic stages were composed into early native boards and
viewed separately with view_image(detail=original). GFX12 triplets/20 cells:
new arms/parent have very similar gray sky, soft building/foliage and mesh;
no clear large texture repair, isolated bright green point persists. ISO100
DSCF3880/f5.6 independent reference is notGT. Analytic6 triplets/12 cells:
dark period8 and faint period16 stripes remain strongly attenuated in both new
arms, while flat noise is reduced. Record the actual view receipt in continued
review; these observations are not completed overall model promotion evidence.

New math audit: centered same-color RAW differences cannot change a constant
sensor-clipped field. Adding a correction on observed-max ADC channels exposes
a second obstruction: hard display clipping can leave positive color error
with exact zero correction gradient under actual sensor-valid-v1 full loss.
Initial one-off inspected this counterexample before freezing the expanded48-case
study; not a preregistered photographic performance trial. No current V77 cause
inferred and no post-hoc gate change.

Mild protocol matrix/WB[2,1,1.5], exposed sRGB[3.6,1.8,.9] gives physical camera
[1.6875,1.845,.72]. At prediction[1,1.1,.72], pre-displayRGB is
[2.107059,1.048235,1.024706], so preview is white while targetblue=sRGB(.9).
Actual full loss.01110120, displayMSE.0006844154, valid physical cameraMSE0,
correction gradient exactly[0,0,0]. Diagnostic interval loss works before display
clipping: exact interior components, lower bound1 at white and upper bound0 at
black. Gradient[-.03921441,-.01960720,0] supplies a direction on censored channels.
GT-only feasible witness[1.848,1.524,.72] gives displayMSE0 while validB unchanged.
It does not recover the true unobservable latent red/green. Oracle is strictly
for feasibility, never input to an inference correction.

Frozen48 cases:3 scenes*2 matrices*4 CFAs*2 observation types (ideal clipping and
actual16bit ADC/black.03/zero noise coefficients). Strong arbitrary phase-aware
AdaptiveRawKernel coefficients/features; all48 head/feature gradients exactly0
on constant fields, state unchanged. All8 coupled-clipped cases show plateau,
nonzero interval gradient and feasible displayMSE<1e-12 with unchanged valid
cameraMSE. The added gate preserves correction0 at every valid measured CFA
position and rejects one-code-below-white input; it does not guarantee unbiased
base denoising. Identity controls do not have the coupled color obstruction.

Independent NumPyFP64 camera/CFA/gamma/mask/spatial/highlight/full-loss/interval
gradient replay64 estimates: max loss-part difference3.98158e-8, gradient2.25691e-6.
Seven focused regression/invariant tests pass1.62s; Ruff and diff checks pass.
These are new prototype-script tests, not a repeated entire1021-test suite.
Main production package and existing checkpoints/loss/renderer remain unchanged.

Actual48 CPU head forwards, zero full restoration forwards, zero DINO loads,
zero source images, no CUDA/optimizer. Scientific Matplotlib plot actually viewed
at original resolution, copied byte-identically. Plan SHA
183fa0f9e5371341fead8cf54c810be8e3aecb35754b529eea62d868d6fd3b0f,
44 frozen files under censored-highlight-gradient-CPU-v1/work. Plot SHA
6c18c29718ba4da8759a2ef0b028492876724454c9af7036a4be904e941d2562.
Publication audit52 source/result hashes,48/8 invariant checks and38 local links.
No scientific crops resized or AI-generated; no source RAF drives read or written.

[Counterexample report](../docs/censored-highlight-gradients.md) and linked source,
case, plot, test and publication receipts document this as an experimental math
probe outside production. A context-predicted censored correction and informative
interval supervision warrant a separate engineering/model study, after genuine
preflights and new fixed criteria. Current V77 gate stays failed; finish its full
review and native closure. Original PROMPT.md and working README V43 pixels remain.
