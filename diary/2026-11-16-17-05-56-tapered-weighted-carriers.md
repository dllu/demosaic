# Tapered weighted carrier discovery pilot

Recorded: 2026-11-16T17:05:56-08:00 (America/Los_Angeles).

Previous attention/context report pushed d7c88f07. The full1164-case original
producer/reviewer remain exact live identities; no original process is restarted.

Two A-only discovery diagnostics use the cached400/far two-direction sensor
inputs, no GT RGB/reference arrays/new noise/neural calls. Native512 complete
edge nuisance is fixed. Inverse-variance conditional weighted-LS spectrum plus
weighted frequency refinement alone misses the weak carrier in all four folds.
Adding the standard fixed pixel-centered separable Hann finds both carriers
in all four folds: strong/weak nearest distances0.16–0.24/0.30–0.76 native bins.
Recipe frequencies are read only after selection for this diagnostic; this is
proposal coverage, not delivered restoration fidelity. All sampled Fourier
benefits agree with independent explicit weighted-LS to below1.6e-16.

Implemented optional frequency_weighting=uniform/inverse-variance/
hann-inverse-variance. Uniform preserves the prior path; weighted modes use
an A-only analytic shot/read variance proxy, nuisance QR projection and exact
frequency-dependent cosine/sine Gram energy. The fixed Hann modifies only
discovery/refinement; amplitude/physical validation/neural nuisance/delivery
remain unchanged.147 numerical tests pass6.73s: explicit weighted-LS agreement,
all4 CFA withholding/NaN invariance and existing model behaviors. Initial test
fixtures used16×20 with a Bayer splitter requiring minimum32; five fixture
failures retained and fixed without production changes. Legacy256 first tile
and full512 frequencies, plus the new Hann diagnostic, reproduce exactly in
12 two-fold checks. Initial reproduction mistakenly compared a512 fit to a
saved256 tile; failed log retained, corrected version uses actual native tile
coordinates/global split.

Launched neural-nuisance-hann512-pilot-v1, plan29235e5497d31a2479aba37aa59c00f6c7a3811e8b1aa80a18672235b573febb,
controller720471/create1794877522.29, predictor720515/create1794877529.99,
reviewer720472/create1794877522.31. Same48 cases/88 exact nuisance fields,
all6 controls/global-local thresholds0/2/4; no fresh neural forwards. Native512,
complete edge search, material256 dimension-only fallback. Independent input
audit passes before correction. Own controllers/workers use CPU16,17; full
original panel stays on18,19. Initial prelaunch schema check used nonexistent
root_forwards instead of new_root_forwards and failed before creating any
worker; original script/log retained, corrected launcher v2 uses actual fields.
Producer closes all48 corrections before score/native audit; separately frozen
reviewer waits on exact producer identity. Results pending at launch.

Fixed future summary chart layout with constrained margins and disabled tick
label offsets; older clipped PNGs remain byte-identical.

All original Hann pilot stages complete normally:162.37s CPU correction,
6.10s scoring/4.42s reporting/8.47s independent audit/2.03s matched boards.
Zero new root/encoder forwards, all48 outputs closed before target scoring.
Independent audit3,819 fields/228 finite/114 material rows/14,131,200 encoded
channels, max3.55e-15. All36 published figures actually viewed in11 exact
unresized contact sheets, including two additional independent-pixel-checked
analytic160 triplets, two neural triplets and both complete protected families.
181 exact compressed archives/source snapshot/native PNGs published.

Analytic Hann400/far weak response2.70250% versus parent0.95794%, strong37.58668%
versus33.78291%; weak-increment RMS11.77761 versus11.78863DN16 (−0.09345%),
quiet4.00872 versus4.00857 (+0.00374%). Both source increment errors improve:
8.82672→8.81821 and14.75054→14.73702DN16. Relative to256 fixed-NN, weak
increment error improves0.423%, but strong response falls41.168→37.587% and
full RGB RMS rises21.70476→21.73732. Weak orthogonal error slightly rises
versus parent. This is a useful optional error/response point, not a broad
quality/default promotion. Most weak detail remains absent; other priors and
near edges remain largely parent-like. Keep both useful operating points.

Matched neural Hann weak2.30418%, quiet+0.06249%, weak-increment−0.03855%
versus parent; source0 increment worsens, source1 improves. Its maximum building
correction1.9535DN16 at[26,352,160,160], versus analytic maximum16.6146 at
[95,204,160,160]. Historical failure ROI retained with analytic13.823DN16.
These are change-from-parent values, never real-reference error scores. Actual
native views: quiet sky, soft bark/fur/foliage, missing fine cab crossings at
both profiles; no clear added broad building bands. All independent real and
native-binned references retain accurate not-GT/qualitative labels; no scores
against real GFX references. Source pixels remain unresized and originals
read-only/excluded from training.

Current producer clarifies weighted-discovery scope for future plans; the
executed plan/source bytes and study.json intervention remain intact. No
running original full256 source/process is modified. Full-panel quality
remains pending.

[Completed Hann report](../docs/neural-nuisance-hann512.md).
