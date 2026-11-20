# Recovering weak detail without inventing texture

Literature and project review, **2026-11-15, America/Los_Angeles**.
The original proposals below were unimplemented when written; the follow-up
links record subsequent implementations and measurements.

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
The [fixed measured-wave GT fit](measured-wave-oracle.md) doubles the additional
bank's global-fit weak response to 19.39%, but quiet error worsens on 56/64 views
and weak-increment error on 46/64. Removing the gain box or permitting phase
rotation adds little. This is target-assisted diagnostic evidence, not an
inference gain or a spatial-head capacity bound; localized discrimination remains unresolved.
The [input-only local conditional-wave prototype](local-validated-waves.md)
now tests that direction: its fixed two-geometry pilot raises far weak response
0.96%→2.80% above V143, with lower quiet/increment costs than the same-candidate
global support. Source1 drives the gain; quiet error still rises versus the
parent and real cab crossings remain missing. All24 cases/native views are
complete. The [full three-prior/all-CFA panel](local-wave-full-panel.md) now
finds400/far weak response1.826%→2.690%, with quiet/increment error
+0.405%/+0.289%. Local support lowers global-support error in all six cells,
while gains remain source-dependent and higher-noise weak detail stays missing.
The frozen full run uses the historical matcher. Real/photo parents are V120;
corrected lineage is explicit. This is an implemented experimental
reconstruction component, not a calibrated confidence guarantee.
Its [matching/harmonic follow-up](local-wave-shapes.md) fixes a valid-pair
assignment failure and tests a richer input-only waveform. H3 doubles the
fixed-pilot far weak response to 5.46%, with higher quiet/increment error and
new building color bands; a nearly matched weak-response H1 threshold has
lower errors. More basis capacity alone does not resolve the fidelity problem.
The [individual-harmonic/background controls](individual-wave-validation.md)
retain lower far quiet/increment error than group support, with less response;
neither removes building bands. Two affine planes further increase quiet error.
Per-component held-out support remains insufficient for the real artifact.
The [whole-context neural nuisance follow-up](neural-nuisance-reconstruction.md)
shares a global CFA withholding partition between88 frozen neural backgrounds
and all analytic tiles. Its completed48-case audit/native review finds less
added quiet/building error, but400/far weak response falls3.686%→0.900% versus
matched conditional analytic H1. Better background prediction still does not
recover missing weak directions. Its [fixed-proposal follow-up](neural-nuisance-fixed-proposals.md)
uses the same88 cached backgrounds, zero neural replay and576 exact analytic
control files:400/far weak response recovers to2.690%, with quiet/increment
RMS−0.574%/−0.133% versus the3.686% conditional analytic control. This useful
quieter operating point still loses response and misses real fine crossings.
The [native512 follow-ups](neural-nuisance-context512.md) lose this gain, returning
near-parent0.957–0.959% weak response. A complete edge-offset search fixes the
far-background geometry and greatly lowers withheld noisy sensor error, but
still misses weak carriers. This separates a real nuisance-model limitation
from the remaining frequency-discovery/reconstruction problem. The
[completed full eight-source256 panel](neural-nuisance-full-panel.md) confirms
lower quiet/increment errors than analytic H1 in all6 cells.400/far weak
response2.299% exceeds parent's1.826%, with parent quiet/increment costs
0.058%/0.055%, source1-dominated response and missing real fine crossings.
The [Hann/inverse-variance discovery follow-up](neural-nuisance-hann512.md)
finds both procedural carriers in both folds and restores2.702%400/far weak
response with weak-increment RMS−0.093% versus parent. Both reused sources
improve that error. Against256 neural, strong response falls and total RGB
error rises. The matched neural arm reduces added building correction further,
with less weak response; real fine crossings remain missing. This is an
implemented useful error/response alternative, not broad weak-detail recovery.
The [local129 amplitude follow-up](spatial-carrier-amplitudes.md) raises
400/far weak response6.241% with lower increment error but severe real building
bands. A frozen-operator diagnostic reproduces actual Hann outputs and shows
only3–5% ungated transfer of known finite weak increments. Local full/null
fits address amplitude dilution while reintroducing background-transfer costs;
localizing carrier amplitudes with a better constrained nuisance remains open.
The [fixed global-background follow-up](global-background-local-carriers.md)
reduces the neural building maximum41.87→15.55 DN16, at weak response6.043%→
4.695%. Analytic bands remain around302.55 DN16, rejecting local nuisance
coefficient changes as the sole cause. Mean synthetic gains still depend on
source1 and real crossings remain missing. A [full source/CFA/noise comparison](global-background-full-panel.md)
is now complete with all cached fields and an explicit paired256-neural
baseline: weak2.299%→2.778%, strong37.032%→48.055%, all8 sources improve strong
response/full RGB error. Mean quiet/increment errors rise; added real cab
ripples fall while fine crossings remain missing. All68 native figures and
paired saved256 panels are actually reviewed. The broader result preserves a
useful stronger-detail tradeoff rather than establishing weak fidelity.
The [fixed-background phase reconstruction](global-background-phase-reconstruction.md)
raises two-source400/far neural weak response4.695%→27.390%, now on both
sources, with quiet/increment errors+2.352%/+0.434% versus parent. Its analytic
arm reaches28.558% with increment−0.539%, but both add larger real building
bands and still miss fine cab crossings. All48 cases/38 actual native figures
are reviewed. This establishes useful additional reconstruction capacity with
mixed error costs, without resolving nuisance discrimination. The global
competing-direction fit also differs from the prior local sinusoidal fit, so
the comparison does not isolate waveform capacity alone.
The [withheld neural-guidance follow-up](neural-guided-phase-pooling.md)
retains28.702% weak response for analytic nuisance while lowering mean quiet/
increment error versus unguided phase; increment error is−0.946% versus parent
with both sources improving. Severe analytic building bands are much smaller,
531.58→130.59 DN16 maximum correction. The primary neural-nuisance arm instead
worsens increment error on both sources. All48 cases/38 actual figures are
reviewed. Guidance helps this measured analytic operating point without
recovering high-noise weak detail or fine real crossings. An input-only
168-operator diagnostic finds only1.01549 maximum global residual amplification,
so a large oblique-projection gain does not explain the checked failure.
The completed [eight-source guided panel](neural-guided-phase-full-panel.md)
retains stronger400/far response, weak2.299%→9.300% and strong37.032%→68.274%
versus256 NN, with lower full RGB error. Quiet/increment errors rise
0.258%/0.606%; the pilot increment gain does not persist. All70 native figures
are viewed; weak real crossings/high-noise detail remain missing. A candidate
that helps a nuisance predictor can still worsen the delivered neural parent.
The [additional fine-band follow-up](fine-frequency-proposals.md) instead
checks discovery: original cab proposals miss both RAW-green fine families.
An additive A-only search finds them, preserving broad carriers and their
correction. Complete48-case/44-figure review shows more cab lattice, with
false purple/green periodic chroma. Analytic1600/far weak0.989%→2.037% retains
quiet error and slightly lowers increment error, driven by one source;
400/far remains identical. Building artifacts/neural1600 errors increase.
The useful proposal gain is implemented, with its limits; finding a frequency
does not validate missing-colour samples or the full delivered profile.
The [sinusoidal fine control](fine-sinusoidal-carriers.md) retains the same
proposals/broad correction, using local full-fit sine/cosine coefficients
with conditional support. All48 cases/46 native figures are reviewed:
NN1600/far increment−3.017% versus fine phase with less weak response;
analytic weak2.037%→1.500%, cab colour grid persists, building bands worsen.
The practical H1 fine constraint alone does not repair the artifact. Tests
also expose faint-colour loss from summing conditional differences and verify
full-fit colour amplitudes/phases with known correct geometry on all4CFAs.
Actual colour/background discrimination remains open; the test is not a
real-scene recovery or calibrated inference claim.
The [joint-colour support follow-up](joint-fine-colour-support.md) makes a
useful real-camera gain: much less cab purple/green tint with the lattice
retained in both profiles/ROIs. The RAW-only diagnostic finds green support
dominating weak R/B despite nonzero fits; joint actual-CFA gain aggregation
keeps separate RGB amplitudes/phases. All48 cases/46 figures are reviewed,
with extra1600/far synthetic response lost and persistent building bands.
The [fresh coloured benchmark](coloured-fine-wire-benchmark.md) adds neutral
and signed-colour fine wires across allCFAs, genuine A-only predictions and
four fixed reconstruction variants;192 corrections/400 rows/40 actual figures
are independently audited. The1600 joint weak gain is almost entirely neutral:
signed-colour weak25.362225%→25.362461%, with increment/colour errors slightly
worse. All-stage errors remain above V120;6400 has no useful weak gain.
Reduced real tint and faithful signed-colour reconstruction are distinct outcomes.
The [whole-image production/context review](weak-detail-global-context-production-review-2026-11-16.md)
therefore remains useful: current DINO still receives only tiles. The
[scene-context implementation/data follow-up](whole-scene-context-next-test.md)
prioritizes aligned whole-scene features alongside local RAW reconstruction,
with same-observation scene/crop training and correct-versus-shuffled-context
controls. CFA preview/query plumbing is tested; no scene-conditioned quality
benefit is established yet.
November17 execution follow-up: the [matched2k/64-source study](whole-scene-context-development64.md)
now finds small quiet-coarse gains, and [complete camera panels](whole-scene-context-camera-review.md)
find partial unseen-camera repair over local-only, still below V120. Correct
spatial placement has no established fine-detail advantage. Both protected GFX
families are actually reviewed; full427 photos continue collecting. The separate
[larger-corpus continuation](full-corpus-scaling.md) is running with RAW domains
retained. These measured follow-ups preserve the original review's cutoff.
The later [edge exclusion](phase-guide-edge-guard.md) improves lower-noise
near-edge frequency selection. The [shared Bayer waveform](shared-phase-shape.md)
slightly lowers far-edge chroma error and loses near-edge weak recovery at
matched quiet RMS. Both tests retain independent RAW validation.
The [existing full-model RAW-attention comparison](raw-spatial-continuation.md)
completes both original20k arms: [V131 targeted quality](v131-endpoint-quality.md)
has faint-ADC +0.14555 dB across four sources with a bark regression, small
ordinary/shadow gains and no convincing new real mesh crossings. V132's
[completed20k/native review](v132-endpoint-quality.md) loses0.40978 dB faint ADC
versus V131, with ordinary+0.00046 dB/shadow−0.00438 dB and no new fine cab
crossings. All20,000 actual clean/noisy input hashes match; original source and
horizons are preserved. The earlier1k faint advantage did not persist, so this
specific RAW-attention continuation does not improve targeted weak fidelity.
V131's [completed broad review](v131-broad-primary.md) finds photo+0.04000 dB
and400/427 source gains, but unseen-camera−0.04381 dB and worst ADC color error
1,816 DN16 versus55.5. Its weakest high-noise band gains amplitude with slightly
higher reconstruction error. An existing fixed physical projection repairs
the color panel to20.0 DN16. Its [completed ADC photo/texture review](v131-adc-projection.md)
adds0.15074 dB ADC-photo PSNR over V131, with382/427 gains, but weakest-band
error rises1.43% and orthogonal error2.63% despite higher projected response.
That available operating point improves color/overall score without resolving
weak-detail fidelity; positive-noise V131 outputs stay unchanged.
The [phase-aligned measurement-aggregation prototype](phase-measurement-aggregation.md)
now tests proposal4 with the same RAW-only H1 discovery and matched H1 control:
local same-color phase averages, edge stopping and A/B conditional validation.
Its [completed48-input/three-prior review](phase-measurement-aggregation.md)
raises400/far weak response2.80%→12.61% versus matched H1, but adds5.42% quiet
and1.95% increment error, with severe building color bands and poor high-noise
results. The completed consistent nuisance-projection follow-up reaches12.68%
with similar error costs and the same building bands. An
[A-only masked-neural background diagnostic](withheld-neural-background.md)
predicts withheld noisy building/cab sensor samples better than the analytic
fit, with blur/artifacts still present. This supports testing a richer nuisance
competitor, without claiming improved delivered detail or calibrated confidence.
The [distant wire/gap intervention](scene-wire-gap.md) holds native
RAW fixed across three whole-scene contexts. The existing spatial 2k
EMA gives almost the same weak response for aligned and orthogonal
guides at both priors. The [expanded matched scene run](expanded-scene-corpus.md#matched-12000-update-continuation)
tests the same adapter on a larger corpus from the 100k parent.
The [isolated RAW line fit](isolated-raw-line.md) uses a measured
exterior guide and disjoint local Bayer support. On fresh partial
ISO400 wires it recovers about 81% of the increment, with 2.40 DN16
of added gap RMS after the short-window support check. Its isolated
geometry rule leaves the standing GFX predictions at their parents.
The [near-ADC training continuation](near-adc-bridge-training.md#positive-noise-results)
gives small positive-noise gains with large saturated-color errors.
The existing bounded RAW corrections yield larger weak-band gains and
repair most of that bias on the retained panels.
The [adjacent donor study](donor-phase-transport.md) finds both directions
in the right GFX cab with local held-out RAW gains. The optional crop
fallback adds visible crossings and keeps the smooth sky. The exterior
phase fit improves continuous ISO6400 synthetic weak-wire response and
extends some patterns into gaps. The right-cab gains still leave uneven
contrast and overly regular crossings in places.
The [smooth support follow-up](smooth-mesh-support.md) removes some
synthetic ISO400 gap texture and exposes false cuts beside steps.
A reserve-fitted step restores those continuous cases in a retrospective
replay. The largest tested ISO6400 false continuation has weak held-out
support for a cut even with exact gap geometry and background.
The [fresh contrast-step panel](mesh-step-continuity.md) finds that
separate wire amplitudes preserve more continuous ISO400 cases and
keep the recovered cab crossings. Direct rear rescaling improves
two independent ISO400 repeats. The largest ISO6400 false continuation
persists, and exact clean backgrounds remove residual false admission
on two synthetic controls where exact strong-wire geometry does little.

The refined foreground step rejects two false ISO400 rear directions
while retaining their true counterparts on fresh draws. Its rear check
weakens one true ISO6400 wire and leaves all eight standing camera crops
identical to the adjacent-donor result. A reduced-amplitude forecast
recovers the high-noise approval in a retrospective diagnostic.
[Refined RAW edge check](mesh-refined-edge.md).

The finite footprint test selects a possible gap on reserved Bayer
sites, then checks the actual proposed attenuation in disjoint forecasts.
It reduces added texture in every fresh ISO400 gap and leaves the
continuous two-wire outputs alone. Most high-noise gap continuation
persists, including under exact guide geometry.
[Finite weak-wire support](mesh-shrunk-footprint.md).

The pooled gap study separates available Bayer evidence from locating
the gap. Exact predictions and three quarters of the samples detect
381 of 384 fresh ISO6400 gaps in six fixed geometries. A larger
footprint search helps an earlier miss and loses one true gap on
the new panel. [Known and measured gap evidence](mesh-pooled-gap-evidence.md).

Average nomination improves the number of admitted high-noise gaps
on independent noise draws. At equal correction strength, the averaged
footprint also lowers fresh crop gap error. The default amplitude
leaves more high-noise gap texture. A bounded refit reduces it with
more attenuation away from the true defect.
[Averaged weak-wire proposals](mesh-averaged-gap.md).

Tapering refit strength reduces exterior attenuation on independent
high-noise gap draws. Separate center and fringe strengths give a
small fresh ISO6400 gain. The largest remaining spatial errors
include an incorrect fitted gap direction, which strength changes
only partly compensate. [Tapered rear strength](mesh-tapered-strength.md).

Refining angle, position and width on the same nomination sites
lowers ISO400 gap error at matched strength and partly corrects one
archived angle miss. Four of five high-noise gaps that reach the
averaged audit in the fresh panel still fail it. Several continuous
ISO400 wires receive spurious cuts. [Refined gap geometry](mesh-refined-footprint.md).

Projecting out the continuing wave retains 85–95% of the exact
ISO6400 test-template norm. Curvature and smoothly changing rear
contrast prevent false cuts in a fresh ISO400 set. The joint
nomination slightly worsens the independent ISO6400 gap errors.
[Gap evidence and smooth contrast](mesh-gap-information.md).

Measured exterior tint gives a small ISO6400 gain on independent
noise draws and more attenuation beyond the gaps. Soft sharing
keeps the fresh and standing outputs bit-identical to the local
audit. Hard sharing can reject true detail when the exterior color
disagrees. [Signed RAW tint check](mesh-donor-tint.md).

A [localized training intervention](scene-local-contrast-training.md)
weakens fine structure inside the native crop while preserving the
rest of each scene. The [matched four-arm run](scene-local-contrast-2400.md)
tests the interaction with spatial scene features. Its 64-photo panel
measures the known fine residual separately from false variation in
an exact flat core. The [ordinary-data pair](scene-local-contrast-2400.md#plain-spatial-control)
used byte-identical observations across 4,800 training photos. On the
eight-photo ISO6400 pilot, spatial context leaves almost the same
coupled increment error and adds more flat-core variation than the
local arm. The matched scene slightly reduces flat-core variation
against the spatial model's own masked preview. The [completed 64-photo
review](scene-local-contrast-2400.md#completed-64-photo-comparison) finds
slightly higher flat-core variation with aligned scene features in
both recipes and nearly identical fine-increment error at ISO6400.
The [preview-resolution intervention](scene-preview-scale.md) finds
that resampling the coarse preview yields similar flat-core gains to
using new finer samples. Filtering scene corrections by output band
has draw-dependent effects on fine error and closely follows the masked
guide on the fainter half. Fine cab crossings remain incomplete in
both real reviews. The fixed photo and camera panels are collecting.

The [64-photo natural-texture evaluation](full-corpus-faint-noise.md)
finds that corpus scaling mainly lowers ISO6400 output variance.
Signed faint fine-band response remains near 12%, with persistent
error after taking the mean across four independent observations.
In the [fixed 427-photo fine-band audit](full-corpus-long100k-weak-band.md),
Corpus 100k recovers more of the weakest band at ADC-only and ISO100.
At ISO12800 the recovered fraction stays near 36.5%, while fine
error falls slightly. This broader panel measures a different
contrast selection and supports the same high-noise limitation.

The [paired luminance study](paired-luminance-detail.md) tests
supervision on the signed present-minus-absent increment above the
frozen Corpus 100k. At ISO6400, both noise draw policies gain about
0.47 percentage points of target-aligned fine response on 64 photos.
Independent-draw increment error rises 0.31 DN16, with more
draw-sensitive output. Requiring support in both 18- and 42-pixel
green windows lowers excess flat RMS at matched correction strength.
The fine GFX cab crossings remain incomplete.

In the [three-redraw follow-up](paired-repeat-stability.md#starting-model-on-64-photos-with-three-redraws),
the paired head lowers the shared fine-increment error by about
300 DN16² under each ISO6400 coupling law. Between-draw variance
increases by 405 DN16² for independent pairs and falls by
39 DN16² for coupled pairs. The follow-up trains against the
draw-dependent term with matched controls.
[At 600 updates on separate photos](paired-repeat-stability.md#response-matching-at-600-updates-on-separate-photos),
the lighter repeat term loses its variance benefit at matched
independent-draw response. About three quarters of the starting
head's added variance on these photos comes from positive
covariance with the parent's fine-increment error.

In the [paired-head input replay](paired-feedback-paths.md),
an independent guide barely changes variance. Subtracting a
mosaic from a different exposure raises variance when the
innovation still contains the query RAW. Moving the entire
guarded correction to an independent exposure brings the
parent-correction covariance near zero and improves increment
error over Corpus 100k. Same-frame innovation smoothing gives
only a small benefit over the response-matched paired head.
The [projected repeat endpoint](paired-shape-stability.md#final-performance-on-the-96-photo-panel)
retains some response lost under the standard repeat loss.
Calibrating to the ordinary control's response lowers coupled
error by 0.085 DN16 and raises independent error by 0.049 DN16
on the additional sources.
The [completed standard repeat run](paired-repeat-stability.md#final-1200-update-evaluation)
confirms the gain reduction. Its stronger loss leaves ISO6400
independent response 0.58 percentage points below Corpus 100k.
Its lighter loss gives higher variance at response matched on
a separate set of photos.

The [readout-row stress test](withheld-row-noise.md) shows that
disjoint Bayer pixels can still validate the same simulated noise.
Holding out complete rows rejects the false bands and often
suppresses weak real waves. The earlier GFX sky correlation check
did not show clear evidence of such dependence at its tested offsets.
The [distant RAW follow-up](distant-row-reference.md) restores
98.19% of the weak horizontal waveform with clean simulated
reference strips and zero observed null activations. The same
estimator can transfer genuine stripe texture from bad references.

On the [64-photo measured-donor test](natural-raw-donor-evidence.md),
including the donor's coarse structure in the query fit reduces
false accepts on masked-detail targets. An independently observed
registered copy improves 7/64 coupled ISO6400 crops above Corpus
100k. A luminance-only lift avoids the added color speckles. No
disjoint donor qualifies on the eight standing GFX comparisons.

The [mesh transmission test](mesh-background-transmission.md) lets a
shared wire geometry change contrast with the local background. In
24 natural-background simulations at ISO6400, delivery with a local
sensor check lowers true transmissive-wire error and adds less variation
in known gaps than an affine lift. A disjoint 24-photo replay reproduces
the gap improvement, and its wire-error difference against affine spans
zero. Affine does better on additive wires and on ISO400 wire error.
The existing adjacent-donor option still shows the two fine GFX cab
directions more clearly.

The [scene-contour aggregation follow-up](query-contour-support.md)
uses disjoint Bayer samples to orient the amplitude aperture. Continuous
near-edge response rises slightly, and independent gaps show more coherent
texture. Supplying exact geometry exposes recovery and false-flat headroom.
The [one-sided frequency screen](query-contour-support.md#testing-nominations-from-one-visible-side)
finds five plausible occluded pairs and admits none on the reserved quarter.

The [bent exterior witness](query-exterior-witness.md) obtains 10.45
points more recovery on occluded fields and lowers increment error after
checking the fitted peak against neighboring frequencies. The extra check
removes an automatic building proposal. Independent gaps retain more added
texture and two strong-only controls still receive new corrections.

The [extra-RAW-quarter follow-up](query-local-gap.md) reduces added
texture in photometric gaps while preserving average weak response at
matched calibration strength. Direct localized gap nomination fails
on the new admitted ISO6400 cases. Both standing outputs match the
preceding exterior-aware fit.

The [checked-harmonic follow-up](query-checked-junctions.md) adds
reserved-RAW support for second harmonics and junction bands once two
directions already have support. Some right-cab crossings become clearer
under both noise profiles. Small false responses remain on exact controls.

The [exterior-donor composition](query-donor-composition.md) tests compatible
and rotated surrounding RAW with byte-identical native inputs. Matching
surrounds enable three extra recoveries. The additional checked band changes
one of them. Both real left-cab profiles show a faint lattice and retain
most of the appearance from the earlier donor fit.

The [wire-shape comparison](query-donor-bandlimit.md) removes unsupported
harmonics from the donor response. It lowers exact soft-pattern error at
matched projection and weakens true sharp wires. With known candidate
directions, a reserved second-harmonic test recognizes 15 of 16 narrow
ISO6400 cases and admits one smooth case. Fine cab crossings remain soft.

The [automatic per-direction shape test](query-shape-routing.md) finds that
evidence for a sharp wire cannot be shared freely with its smoother neighbor.
Keeping only supported second harmonics reduces the other wire's shape error
at matched response. Truly narrow ISO6400 wires retain sharper profiles
with the earlier full ribbon. Gap spill remains.

A [shared weak-waveform deficit test](query-shared-gap.md) lowers added
gap RMS from 57.77 to 48.64 DN16 on additional ISO6400 photographs with
elliptical and strip gaps. Nearby intact recovery falls 2.99 points, and
one continuous dip is cut. Giving the fixed scorer the true footprint
admits nine of ten active gaps versus seven with the automatic search.
Both standing GFX families retain the preceding crops pixel for pixel.

On 24 additional photos, [two-sided gap localization](query-gap-shoulders.md)
retains the same intact response at equal leakage as uniform attenuation of
the shared edit. Green with automatic and exact geometry admits the same
six eligible gaps. Adding red and blue confirms two more known footprints.
Automatic cross-color nomination has mixed results across the two panels.

The [reserved Bayer colour replay](query-signed-colour.md) uses the
measured weak phase to condition signed colour at fixed luminance. It
gains 4.35 aligned chroma points on 16 ISO6400 colour fixtures and
preserves the neutral replay results. The eight standing GFX outputs
reproduce the preceding fit. Supplying the planted frequency pair
recovers chroma confirmation in three of five missed high-noise fields.

The proposals below remain the original November 15
assessment; measured follow-ups are linked here rather than rewriting history.

The [whole-image RAW strength prior](context-strength.md) assigns different
gains to the standing sky and coarse fence with negligible reconstruction
change at matched response. Exact-target scaling of the fixed proposal lowers
independent pooled ISO6400 error by about 0.2%. The
[native Bayer green innovation comparison](green-phase-innovation.md) changes
the proposal itself and lowers matched-response error near strong steps,
with higher whole-core error and incomplete fine crossings. The
[full-epoch scene trial](scene-full-epoch.md) trains separately on the
matched larger source schedule. At the [64-photo 20k review](scene-full-epoch-20k.md)
both arms lower independent ISO6400 fine error over Corpus 100k with
lower fine response. The correct and mismatched distant views are nearly
tied, and both standing real scenes retain incomplete fine cab crossings.
The [matched 25k photo review](scene-full-epoch-25k.md) lowers independent
ISO6400 flat RMS by about 0.10 DN16 over 20k in both arms. Fine response
falls another 0.20–0.25 points. The effects of correct and mismatched
distant context remain nearly tied. Both standing GFX comparisons are
complete at 25k, with a smooth sky and incomplete fine cab crossings.
The [matched 30k review](scene-full-epoch-30k.md) recovers 0.121 independent
ISO6400 fine-response points in the local arm at 0.037 DN16 higher
flat RMS. The 30k spatial arm still ties the mismatched distant control
on response and exact-flat error at ISO6400.
The completed [35k comparison](scene-full-epoch-35k.md) lowers
independent ISO6400 fine-increment and fine-flat RMS in both arms
versus 30k. Mean fine response rises slightly with intervals spanning
zero and remains below Corpus 100k. Matching the distant preview
changes fine response by 0.002 points versus the wrong preview.
The 35k standing crops still have incomplete fine cab crossings.
The [matched 40k review](scene-full-epoch-40k.md) finds a further
0.022 DN16 fine-flat reduction and 0.119-point response loss in the
spatial arm at independent ISO6400. Correct distant conditioning
gives little fine-band change versus the wrong distant view. Both
standing fine cab crops retain missing intersections.

[Directional gap supervision](directional-gap-training.md) separates
strong-wave repair from the missing weak band in exact gaps. It gains
0.44 intact wire-response points at similar total gap correction.
Error in the missing weak direction rises slightly and fine real
intersections remain incomplete.

[Competing-wave validation](competing-wave-validation.md) improves
held-out detection when the weak waveform phase is supplied to the
controlled test. At native RAW-only inference, the trained router's
registered feature gains are small and fine crossings remain absent.
Subtracting the dominant wave separately in each disjoint donor
reduces validated weak-phase matches at ISO400. The phase nomination
and the spatial delivery of any extra correction both matter.

[Wider disjoint Bayer neighborhoods](wide-bayer-neighborhood.md) improve
planted phase agreement and increase validated ISO6400 intact matches by
5.47 points with eight donors. An all-bin flat calibration shrinks the
apparent detection gain. At similar added gap RMS, the trained head
lowers intact weak-band error and raises absolute gap error. The right
cab gains a little diagonal definition with incomplete crossings.

[Adaptive Bayer blending](bayer-phase-shrinkage.md) learns bounded
weights for the difference between two frozen neighborhood operators.
Matching the absolute change inside gaps makes the constant and adaptive
blends effectively tie on planted wires. A 0.061-point natural-photo
response gain survives at similar flat change, with small RMS costs.
The ablation attributes nearly all the measured recovery to the
amplitude change along the original coefficient phase.

[Disjoint exterior Bayer phase](bayer-phase-quadrature.md) tests a new
perpendicular correction. An exact-target probe shows substantial residual
phase error. Cardinal and diagonal RAW neighborhoods estimate enough of this
error to lower planted ISO6400 intact RMS by 2.58 DN16 and gap RMS by 1.88.
The same rule adds 0.894 DN16 of exact-flat RMS on natural photos and leaves
the fine cab crossings incomplete. Local green phase by itself calibrates
to zero. The useful evidence is strongest for coherent repeated structures.

[Distant Bayer phase gating](bayer-distant-phase-gate.md) checks each frozen
proposal against four disjoint 32-pixel stations 64 pixels away. The new
gate drops the fixed phase natural-flat cost from 0.894 to 0.145 DN16
and retains the planted-wire benefit. Its advantage over shifted
measurements is smaller. Rotating the directional weights changes
little, suggesting that correctly placed evidence is more important
than these particular tangent weights.

[64-pixel Bayer carrier fitting](bayer-carrier-scale.md) finds both
cab spacings in the high-ISO exterior RAW and verifies their support
on the two green lattices. Target fits over 64 pixels admit the weaker
direction more often than 32-pixel fits. The resulting constrained
crop correction adds 12.26 planted ISO6400 response points and visibly
clarifies the real cab lattice. True-gap weak leakage and over-regular
lattice contrast remain. The path is inactive on the natural-photo panel.

The subsequent [local amplitude check](bayer-amplitude-envelope.md) reduces
ISO400 weak-band gap error by 1.176 DN16 over the 64-pixel fit while losing
0.132 intact points. At ISO6400 adding other Bayer colors increases the
number of accepted local fits with little impact on gap error. The Python
crop API reproduces the base fit on all tested synthetic and standing crops.

[Joint geometry across disjoint Bayer windows](bayer-shared-phase.md)
allows each window its own amplitude and phase. It loses 0.211 planted
ISO6400 response points versus the fixed 64-pixel fit. With true geometry
supplied, the same delivery gains 1.50 weak-response points on bent fields
and slightly increases the weak-wave projection inside gaps. The central
greens provide inadequate evidence for the weak bend. Both standing
fence reviews retain their existing intersections.

[Exterior Bayer bend estimation](bayer-exterior-bend.md) increases the
spatial baseline to eight disjoint windows. With fixed exact spacing it
lowers weak phase error to 0.004 cycles and gains 1.55 response points.
Fitting the center and bend jointly from noisy RAW gains 0.387 points
after the original eligibility rule. Only three of twenty bent draws
qualify. The four cab comparisons reproduce the fixed fit at display
precision.

[Bend-aligned donor spectra](bayer-warped-spacing.md) compensate the
opposite apparent frequency shifts in the exterior RAW windows.
A crop-checked fallback adds 5.24 weak-response points on development
fields. Both exterior proposals fail the central check on independently
replayed bent fields, and the standing crops reproduce the prior output.

[Cross-green carrier agreement](bayer-cross-evidence.md) pools local
sine and cosine agreement after exterior nomination. On 24 further bent
backgrounds it passes two more present draws than the calibrated held
residual, with no new activation on 12 eligible absent-detail draws.
The weak-only correction gains 0.10 response points with 0.09 DN16 lower
increment RMS, at higher absolute gap RMS. Sparse exterior proposals
and incomplete standing fine crossings remain the main limits.

[Closer disjoint Bayer donors](bayer-near-donors.md) find two previously
missed bent draws. The eight-photo replay gains 3.62 response points and
lowers increment RMS 1.80 DN16, with 0.95 DN16 more coherent projection
in exact gaps. The 24-photo replay delivers no new near fallback.
Nearby RAW supports the inherited right-cab frequencies, while the
reserved crop rejects new fine geometry. The checked refit gives a
small change to the coarse fence.

[Local Bayer deficit checks](bayer-local-deficit.md) compare inner and
surrounding carrier coefficients across reserved greens. A large phase
shift can look like an amplitude loss. Evidence in the perpendicular
phase rejects all 48 false cuts on the controlled shift and preserves
the true-gap attenuation. On 24 bent backgrounds the veto retains a
0.107 DN16 coherent-gap reduction versus equally strong uniform
attenuation. Absolute gap error changes little, and real fine crossings
stay incomplete.

[Local phase rotation](bayer-local-phase-transfer.md) uses each green's
inner phase to predict the other green at the surrounding amplitude.
On 24 held-out backgrounds with planted local shifts, recovery gains
2.25 response points with supplied geometry and 0.93 with noisy-only
donors. The opposite rotation raises error. Rotation changes only
10 automatic shifted crops and gives little gain on smoothly varying
carriers. The viewed fine cab intersections stay incomplete.

[Rotation toward the missing signal](bayer-phase-residual.md) subtracts
the frozen parent's local carrier before choosing the correction angle.
At matched coefficient magnitude it changes the automatic shifted
center by +0.007 DN16 RMS and +0.053 response points. The audit of
single-direction exterior donors recovers six additional planted weak
frequencies and one unmatched frequency on the later 24-photo replay.
The reciprocal spatial check keeps four of the six weak frequencies
and the unmatched one. This is evidence about nomination coverage.
Standing fine crossings are still incomplete.

[Delivering a checked single direction](bayer-single-direction.md) lowers
fine-increment RMS by 0.66 DN16 and adds 1.42 response points on 24 planted
bent fields. Coherent gap residue increases. Local deficit attenuation
recovers 0.036 DN16 of that cost at matched correction energy. Testing a
competing step gives little change. The guarded routes abstain on all
192 captures from 64 sources with unplanted detail and leave both standing
fence families at their prior outputs.

[Exterior texture covariance](scene-raw-covariance.md) removes the
requirement for a repeated carrier and learns directional power from
disjoint measured RAW patches. On 48 held-out natural photographs it
gains 0.655 points of ISO6400 response with 1.673 DN16 higher increment
error. Equal directional power gives nearly the same response at
matched added flat RMS. A same-scene swap across independently drawn
captures removes 0.596 DN16 of the excess error at the same correction
energy. This is evidence of same-capture parent and correction error
coupling. A stricter whole-parent-pattern lift offers little recovery.
Both standing fine fences remain incomplete.

[Complementary Bayer checks](split-bayer-neural.md) improve noise rejection
when the tested measurements come from the opposite half of the mosaic.
The half-input guides lose fine detail and can add flat structure. At a
matched quiet dose, checking an addition above the full-input estimate
gains only 0.003 ISO6400 response points with more fine-increment error.
Both standing fence families keep incomplete fine cab crossings.

[Paired full-sampling checks](full-sampling-detail-check.md) retain every
Bayer site by adding and subtracting the same simulated perturbation.
The opposite-view check reduces same-view fine error, with just 0.018
ISO6400 response points added above Corpus 100k. Calibrating a wide
boost to match fine response over-amplifies coarser contrast. Confining
the gain to the measured band preserves much of the coarse structure.
The half mix still raises fine-increment error by 0.65 DN16 and keeps
fine cab crossings incomplete.

A [regional endpoint mixture](scene-gated-mixture.md) uses local
activity and optional disjoint scene texture to combine Corpus 100k and
spatial 40k. A bounded luminance boost preserves most parent response
and lowers exact fine-flat RMS by 0.209 DN16. Upper-band error rises.
Replacing the spatial checkpoint with its matched local counterpart
weakens the flat benefit, while shuffling the outer gate features
changes little. Fine cab crossings remain incomplete.

A [band-limited refit](scene-mixture-upper-band.md) filters the actual
signed correction after spatial gating. It lowers both fine-flat and
upper-flat RMS on the fixed 48 photos and a separate 32-photo
confirmation at independent ISO6400. Fine response remains close to
Corpus 100k. The other draws retain the flat benefit, with small fine
increment costs in two conditions. Both standing GFX scenes retain their
existing fine crossing limits.

A [Bayer-gated refit on local 20k](quiet-parent-phase.md) separates
attenuation along the parent phase from additions supported by the
exterior phase and two central Bayer groups. It recovers 7.74 points
of intact ISO6400 wire response and lowers absolute gap RMS by 3.64 DN16
over local 20k. It raises intact error and the exact-flat photo floor.
Separate attenuation and addition gains fail to recover the Corpus 100k
natural response at the parent flat RMS on the calibration photos.

A [local RAW activity comparison](phase-activity.md) puts a smooth
window gate on the same frozen correction. Detrended local self-power
gives more response at lower exact-flat RMS than fixed scaling on
independent ISO6400 photos. A stricter gate gains 0.33 response points
with parent-level flat RMS but suppresses most of the nominal fine-cab
correction. Green cross-power helps detect controlled stronger waves.
For the weakest waves its center-window detection is close to chance,
and many independent exact flats contain at least one active window.

[Reserved Bayer waveform checks with a local edge](phase-edge-validation.md)
keep the exterior nomination and the learned correction fixed
while comparing two backgrounds inside each 32-pixel window. At
the same gain, adding the edge reduces false correction in
constructed gaps from 15.45 to 11.76 DN16 and improves held-out
planted-wire response by 0.27 points over the affine fit. The
photo-calibrated contrast retains more nominal right-cab diagonals
than local power with incomplete crossings. Natural-photo response
still favors local power at similar flat RMS.

[Learned mixtures of local power and edge contrast](phase-correction-mixture.md)
bound each complex correction within its fixed expert gains. On
held-out ISO6400 wires the conditional mixture gains 1.42 response
points and lowers absolute gap RMS by 1.70 DN16 versus local power,
with greater change inside the gaps. On independently corrupted
natural photos, scaled local power retains 0.10 more response points
at similar flat RMS. The mixture primarily draws on edge evidence
for the nominal right cab, where the fine crossings remain incomplete.

[Within-window phase localization and directional gap attribution](local-phase-envelope.md)
finds that 65.02% of the conditional correction energy inside known
weak-wire gaps belongs to the continuing strong wire. The missing
weak family accounts for 0.13%, including phase-shifted waves
of the known bands. Suppressing the entire gap correction would
discard a useful strong-wire repair. The within-window modulation
brings little improvement at matched strength and leaves the real
fine crossings incomplete.

A [dense regional context replay](scene-regional-context.md) gives that
trial's spatial 12k checkpoint a registered higher-resolution neighborhood.
In the additional 48 fixed fields, quiet error falls versus coarse,
resampled and mirrored context. Fine response remains nearly constant.
Previously measured fence frequencies fit on the denser preview pixels,
while the finest scene feature grid cannot represent their native spatial
oscillation directly. The real fine cab crossings remain incomplete.

The [green alias follow-up](quincunx-green.md) separates two native
frequency classes missed by one packed plane alone. On 32 planted
cases with a stronger shared alias, it adds 0.086 percentage points
of weak response over principal-only at matched flat addition.
Disjoint fold agreement and exterior RAW substantially reduce unscaled
flat correction, with limited delivered gain on the exact-target
and standing native reviews. This tests phase accuracy and noise
rejection within a fixed reconstruction, with fine cab junctions
still missing.

**The next useful step is better discrimination between weak structure and
noise/edge leakage, coupled with training that rewards that distinction.**
The project has demonstrated real detail gains, but increasing response alone
has repeatedly increased false texture. I would first evaluate the prepared
shared-edge data intervention, then investigate genuinely withheld-sample
evidence and edge-aware local reconstruction. A larger modern restoration
backbone remains a worthwhile comparison, but it would not by itself explain
or remove these failures.

A [surrounding RAW spectral prior](scene-spectrum-detail.md) changes the
native proposal by frequency. Its exact-target test finds a small error
advantage over transposing the spectrum, with little difference from
exterior mean power. Matching the retained parent phase reduces false
texture and leaves fine cab crossings incomplete. A [learned wider-band head](learned-spectral-detail.md)
adds 0.95 ISO6400 wire-response points over matched total-power
conditioning. The full correction raises wire error and known-gap
texture over Corpus 100k. The native fine cab crossings stay incomplete.
[Exact gap supervision](learned-spectral-gaps.md) lowers paired error in
known breaks and loses signal in continuous dips. Checking a phase from
disjoint green windows against local Bayer samples lowers absolute gap
error slightly at comparable added texture and yields an uncertain
intact-response gain. [Refining the phase between FFT bins](subbin-spectral-witness.md)
raises held-out ISO6400 intact response 0.50 points and lowers absolute
gap RMS 1.30 DN16 at similar added gap texture. Direct gating of a
stronger analytic lift loses signal at matched gap change. Real fine
crossings remain incomplete. [Indexed real Fourier extraction](compact-spectral-witness.md)
reproduces that earlier phase path at lower feature cost. Learning from
reciprocal green pairs lowers absolute gap error by 0.20 DN16 at comparable
texture, with little difference in intact response.

The [Bayer-gated regional damping study](scene-mixture-wire-gaps.md) tests
true interruptions in weak wires above the band-limited regional mixture.
It improves the ISO6400 intact-increment error by 0.370 DN16 while losing
0.109 response points. The weak-band gap change is small, and error in the
strong carrier that continues through the gap rises. A separate photo
cohort with fresh noise confirms lower fine-flat and increment error.
The data support a quieter operating point with lower response.

The [phase-aligned green follow-up](green-covariance-refit.md) separates
directional covariance from the learned restoration and compares a
direct measured-green residual. Both fits select zero added correction
under the previous error budget. On 24 fresh natural photos the
local-only 47.5k EMA lowers fine increment and flat error versus
Corpus 100k. The matching spatial checkpoint loses weak-wire response
relative to reversed exterior on the 24 fresh wire backgrounds.

The [Corpus/local frequency blend](local-band-mixture.md) chooses a
low-frequency correction with zero weight in its fine branch. On 24
additional wire backgrounds it lowers intact error by 0.571 DN16
and raises exact-flat luma 0.457 DN16 versus local 47.5k. A fixed-gain
reversal test finds little alignment benefit. The [completed local
50k replay](local-50000-scoped.md) retains the prior checkpoint's
natural improvements. Upper-band flat noise and incomplete cab
crossings persist.

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
| [Shared-edge comparison](shared-edge-comparison.md) and [consolidation](architecture.md) | Complete matched training/native review; small quiet/flat gains; repeatable runner and retained models | Lower mesh response, persistent real fringes/crossing losses; engineering consolidation alone is not a quality gain |

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

The [reserved Bayer replay](query-bayer-reserve.md) uses separate
quarters for nomination and conditional testing, then fits the remaining
two quarters. It automatically makes both directions from the standing
right cab clearer and leaves the sky unchanged. Fresh planted weak-signal
tests show lower gap leakage and slightly lower recovery than the exterior
full fit. The frozen neural parent still sees every sample.

An exterior-adapted contrast combines a phasewise affine score and
a nearest-same-color innovation. The latter residualizes the known
candidate through the same stencil as the RAW. On 64 fresh backgrounds
with supplied nominal frequencies and RAW-estimated phase and width,
the ISO6400 false count drops from 15 to 10 and the true count from
44 to 41. Half-bin errors largely erase the false-count benefit.
The bounded lift recovers 13.53 signed response points, with a positive
false-detail tail and an overly regular local right-cab grid.
[Exterior wire verification](wire-exterior-verification.md).

The [held-out frequency adjustment](wire-frequency-refinement.md) tests
169 local frequency pairs on separate exterior blocks. On a new 64-source
panel, the stronger rounded guide moves from 0.395 to 0.341 bins of median
error at ISO6400, with the same 42 true and six false calls. The half-bin
radial stress retains mixed gains and larger false-projection tails.
Both directions of the archived left-cab donor pair pass the exterior
strength test. Local validation still leaves the crossings incomplete.
This separates better exterior frequency estimates from evidence for
the spatial extent and amplitude of the wire inside the query.

The [exterior-phase transfer measurement](local-exterior-phase-transfer.md)
finds good phase transfer on the right cab and an 87.8° median local
discrepancy for the first left direction in 64-pixel windows. A closer
ring supplies the phase for a separate 32-pixel delivery area. At
similar weak response it lowers continuing-strand error by 2.361 DN16
versus a local fit at the same width. Nominal local64 recovers more
weak signal, and the ring leaves fine GFX crossings incomplete.

A [wide-fit support replay](local-center-guard.md) holds the 64-pixel
training lattice and 32-pixel delivery fixed. Testing the wider
coefficient only on the central held green loses 4.152 weak-response
points versus a broad held-green check. At matched low response it
lowers continuing-strand error by 4.596 DN16, with similar false
projection. The standing center check makes smaller corrections to
the fine cab mesh, whose crossings remain incomplete.
An exploratory lower cutoff retains 1.927 points over Local 50k
with no activation in 56 reused exact-flat crops. Lowering it
further gains more response and admits 37 flats. This frames the
tradeoff at the level of the complete selection procedure.
A [fresh two-draw study](local-nested-support.md) combines the broad
and center checks with frequency donors outside the full synthetic
query. At comparable weak response the combined check reduces
continuing-strand RMS 4.203 DN16 versus broad verification. It has
zero edge-only and uniform activations in 64 crops per role and
two flat-core activations. Center 3 has nine flat-core activations
on the same new panel. The real fine cab requires closer disjoint
donors and still contains incomplete crossings.

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

The [directional support comparison](wire-segment-support.md) removes
the competing wave in each CFA phase and estimates local support across
and along the candidate wire. On 48 new photos with partial and staggered
breaks, ISO6400 localization loses 0.323 weak-response points and adds
0.178 DN16 false projection versus uniform at matched correction RMS.
Giving the same lift the exact break mask adds only 0.55 points.
The real left cab still lacks connected crossings under both profiles.
More usable signed amplitude is needed alongside improved placement.

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

The [joint mesh follow-up](joint-mesh-phase.md) fits the rear wire on the
part of each phase cycle left uncovered by the front wire. It suppresses
the additive fit's junction error on constructed occlusions. Uncertain
local support and unsupported real exterior phases still limit delivery.

The [regional Bayer contrast test](wire-regional-amplitude.md) keeps
that support fixed and pools phase-compatible measurements along the
wire. At equal correction energy, the independent ISO6400 preserved
luma gain is 0.033 DN16 and the response interval spans zero. A
wider amplitude cap improves the paired response and also brightens
the overly regular cab lattice. The two directions still lack connected
crossings in the left ROI.

A [held-green complex envelope](local-carrier-envelope.md) tests
locally varying phase and amplitude with a fixed broad and central
Bayer gate. It gains 0.183 weak-response points on 20 new warped
photo fixtures. At comparable response, continuing-strand RMS
rises 1.509 DN16. A known-phase diagnostic gains 0.920 points
and increases weak-window admission from 129 to 209 without
activating its controls. The real cab shows small changes.

[Whole-photo patch covariance](scene-patch-covariance.md) tests a
second use of exterior measurements. It learns correlations between
native cosine modes from nearby or visually similar exterior patches
and applies them to the query's signed Bayer innovation. The two-green
check improves response at fixed added correction energy, with higher
independent increment and flat error. The simpler diagonal control
also gives lower error in a repeat-pattern simulation at matched
response. Both standing GFX families were viewed.

[Separate donor validation](scene-patch-crossfit.md) lowers
repeat-pattern flat error from 27.01 to 15.44 DN16 at similar
response. At matched wire-flat error, adding the query check
gains 0.109 points over the earlier confirmed diagonal. Natural
fine error rises. The tested 16-pixel basis covers the measured
real cab peaks and starts above the longer planted-mesh
fundamental. The real ROI still has incomplete crossings.

[Wider Bayer windows](scene-patch-width.md) preserve the frequency
band while increasing native support from 16 to 32 pixels. They
reduce continuing short-wire error in true gaps by 3.85 DN16 at
nearly equal flat error. A separate band recovers more of a planted
24–35-pixel fundamental. The wire-calibrated strengths increase
natural-photo errors, and the native cab crossings stay incomplete.

[Dense nearby donors](scene-dense-atlas.md) raise the nominal left
cab correction from 0.057 to 0.287 DN16 RGB RMS with the same
gain. Proximity weighting on the sparse atlas raises short-wire
response by 0.242 percentage points at a matched flat budget.
The wider natural-photo test still favors the frozen parent on
fine-increment and flat error.

[Phase-paired donor power](scene-phase-power.md) retains the same
dense donor geometry and assigns one validated power to each
sine/cosine pair. Real left-cab peak projections improve at equal
added RGB energy. The short-wire gain curve shows lower false
projection and higher exact-flat error at the same recovered
response. The real cab intersections remain incomplete.

[Query phase consensus](scene-query-consensus.md) restricts amplitude
updates to the phase supported by both query greens. Continuing-wire
error falls 0.198 DN16 on 24 independent off-grid photo backgrounds.
False gap projection changes by 0.004 DN16. Median weak-carrier energy
in a single Fourier pair falls from 63% on retained wires to 44% off
grid, where the dense cosine prior recovers more intact detail.

[Shifted Fourier grids](scene-staggered-phase.md) raise median
best-pair coverage from 56% to 83% in the fresh clean-carrier
test. On a second independent 24-photo panel, averaging the four
grids lowers exact-flat RMS by 0.092 DN16 versus earlier radial,
with similar intact response and false gap projection. Selecting on
one donor split and validating on the other gives a lower mean
fresh response. At equal correction energy both measured
right-cab peaks gain, with no clear visual recovery of fine crossings.

[Joint Fourier support](scene-coherent-fourier.md) validates pooled
power across neighboring shifted bins while the delivered correction
keeps each bin's query phase. On 32 unused photo backgrounds it gains
1.004 points of weak response and reduces continuing-wire error by
2.979 DN16 against four-grid averaging with similar false gap
projection. Dense cosine restores more of the intact weak direction.
Natural fine error rises, and both cab ROIs retain incomplete crossings.

[Neighboring RAW phase](scene-phase-neighbors.md) confirms each
center pair on two disjoint nearby windows. Across-wire checks
lower continuing-wire error by 0.45–0.81 DN16 across three earlier
off-grid panels after matching natural fine-increment error on
separate photos. False weak projection changes little. The gains
are larger at the wire-flat calibration, where natural flat error
also rises. No clear real cab crossing gain is visible.

[Pooled center and neighboring phase](scene-pooled-phase.md) lets
disjoint neighboring samples strengthen a marginal positive center
measurement. Fully pooling the scores raises continuing-wire error
in three replays at the matched natural limits. A supplement confined
to weak center scores has smaller regressions and little separation
from its phase-rotated control.

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

In the completed full-trunk redraw study, averaging the signed increment
before applying its loss raises response and lowers the error shared
across redraws. For an individual restoration under independent noise,
draw-sensitive variance rises more than shared error falls. The planted
wire tests also show additional weak-direction residue in true gaps.
[Mean versus individual redraw loss](local-redraw-average.md).

In a matched continuation from the mean endpoint, penalizing the
variation across pairs lowers exact-flat fine error even at matched
natural response to a mixture of the previous endpoints. The cost is
lower weak-wire response. Direct supervision of the absent direction
inside planted gaps restores a little wire response and lowers total
gap error, with a small and uncertain change in weak-direction residue.
[Repeat and gap losses](local-redraw-stability.md).

On 16 held-out wire backgrounds, the exact clean increment accounts for
93% of the repeat model's shared error and 0.11% of its draw-sensitive
variance. An aligned signed loss gains 1.26 weak-response points over
its matched repeat control across fresh draws. Flat and weak-direction
gap error are nearly unchanged. Most of the added variance is outside
the target. In exact gaps, further training attenuates the continuing
strong wire by 9.24 points relative to the starting model. Fine cab
crossings remain incomplete.
[Signed wire supervision](local-wire-response.md).

With a signed loss on the remaining strong direction, strong-band response
rises 16.86 points inside exact weak gaps. An independent double-gap test
gains 8.04 points on true continuation with little change in false strong
response, while flat error increases. In a Bayer diagnostic with the wire
shape supplied, exact subtraction of the reference background separates all
draws. Local affine subtraction leaves eight false continuations, all on
four backgrounds with coherent projected texture. With the gap and clean
waveform supplied, replacing only the recovered strong component lowers
gap error more than the full trained update. [Continuing-wire supervision](local-continuing-wire.md).

A frozen-parent luminance correction with signed gap supervision nearly
shuts off when its confidence sigmoid can approach zero. Keeping a 0.25
minimum gain on the band-filtered output restores 0.49 weak-response
points and adds 0.35 DN16 flat-region error. Just 5.47% of delivered
energy in the gaps aligns with the true continuing wire. The separate
double-gap test retains the gain on true continuations; the standing
cab crops still have incomplete crossings. Separate supervision for
support and signed direction is the remaining question for this route.
[Factored luminance correction](local-factored-wire.md).

Paired support supervision retains the gain-floor head's weak response
with 0.17 DN16 less exact-flat wire error. Its confidence gate averages
24.63% with a true continuation and 24.48% in the textured double gap,
versus 3.94% on the exact flat. Adding a clean signed target to the
ungated proposal greatly lowers delivered amplitude, with lower
response at matched natural flat error. Gate confidence distinguishes
background activity much more strongly than continuation in this trial.
[Separate phase and support](local-wire-gate-support.md).

A [bounded Bayer gain pilot](local-bayer-gain.md) learns from
delivered luma reconstruction error with the parent and the
verified RAW waveforms frozen. Its nominal weak-response gain
over the fixed combined gate is 2.787 points, with lower
continuing-strand error. At matched response that error rises
6.252 DN16. Broad held scores and surrounding statistics have
little effect on the held-out wire scores at this budget.
The broad arm reaches the amplitude cap in 87.1% of accepted
intact-wire directions. An exact-target gain fit with the same
objective also gives up some weak response to reduce false
weak projection.

[Regional weak-wire training](local-regional-wire.md) starts both
full-trunk arms from Local 50k with 1,024 distinct sources each.
The local weak-response term compares nine subregions against the
whole-core term. Both arms explicitly penalize the absent direction.
At [128 updates](local-regional-wire-128.md) the regional term slightly
lowers fixed natural fine error and false weak-direction projection.
The continuing stronger direction through a weak gap has higher RMS
error, and the weak direction loses signed response. At [512 updates](local-regional-wire-512.md),
continuing-strand error is lower on both wire panels, with still weaker
second-direction response. On the off-grid panel the regional arm also
raises wire-flat RMS by 1.902 DN16 versus Local 50k and recovers
slightly more target-aligned detail on the separate natural panel.
At the [completed endpoint](local-regional-wire-1024.md), the off-grid
continuing-strand gain grows to 3.100 DN16 versus whole-core supervision
with 0.733 points less weak response. Matching blend strengths on 16
calibration sources leaves a response gap on the other 16. The regional
blend has lower flat RMS, and the differences on their eight true gaps
are unresolved. Both native cab crossings remain incomplete.

On 32 groups from that recipe, the weak terms are orthogonal to the
exact-flat and strong-gap controls at the restored pixels. Through the
shared parameter weights, both terms frequently oppose the flat and
weak-absence controls. Removing all three control directions leaves
median fractions of 64.4% and 77.3% of the whole-core and regional
gradient norms, respectively. These are first-order predictions
at the starting checkpoint. [Regional wire gradient audit](local-regional-wire-gradient-audit.md).
The [finite AdamW follow-up](local-adam-protected.md) starts from the
completed raw checkpoint and its saved moments. Relative to a
norm-matched control, direction correction lowers flat RMS by
0.00299 DN16 on 32 separate photos. Both gap intervals span zero.
The weakest half loses 0.00500 weak-response points. This separates
a transferable flat effect from the gap gains on the photos used
to compute the update.

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

The [pre-Bayer optical replay](sensor-optical-transfer.md) tested five
frozen EMAs on the same 32 off-grid backgrounds at two added blur widths.
With shared photon counts and read noise across doses, Local 50k recovered
22.44%, 18.99% and 14.59% of the original sharp weak signal at σ 0, 0.55
and 0.85 native pixels. It also recovered a smaller fraction of the signal
available after blur. Regional supervision kept lower continuing-strand
error than whole-core supervision and recovered less of the weak strand at
both blur widths. Keep sharp examples and a separate blur holdout in a
matched augmentation test. The [mixed-optics continuation](local-optical-mixture.md)
uses the same 1,024 ordered training sources as the sharp regional control
and reserves 24 fresh backgrounds for the σ 0.85 comparison.
The [128-update development review](local-optical-mixture-128.md) finds
0.247 points more sharp-normalized weak response at that dose versus the
matched regional control, with 0.031 DN16 higher false projection. The
gain on sharp inputs is 0.381 points. The training audit finds only 21
of 256 blurred wire groups in the test's 7.2–9.25-pixel period range.
At the [512-update midpoint](local-optical-mixture-512.md), the mixed
arm loses 0.361 weak-response points at σ 0.85, with higher quiet RMS
and less false weak projection. The data preflight increases the
blurred wire coverage in that period range from 21 to 63 groups.

The [Bayer evidence replay](optical-raw-evidence.md) separates sampling
from restoration. At σ 0.85, detection with phase fitted on separate
exterior pixels rises from 49.2% to 90.2% when the local window grows
from 32 to 64 pixels. The larger window also improves detection in the
lowest-SNR half. This replay supplies frequency, masks and nuisance
geometry, and uses a strong synthetic exterior carrier. The [trained
endpoint](local-optical-mixture-1024.md) has completed the 24 fresh
optical sources. At σ 0.85 its primary weak-response difference versus
sharp regional is −0.030 points [−0.219, +0.167], with 0.677 DN16
higher flat RMS. Fine cab crossings remain incomplete in both native
GFX reviews. Blending to equal weak response on the earlier sources still
adds 0.296 DN16 flat RMS on the 24 fresh sources. The fixed unseen-camera
mean falls 0.02032 dB versus sharp regional.

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
