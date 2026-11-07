# Fine mesh training distribution preparation

Recorded: 2026-11-07T11:26:29-08:00 (America/Los_Angeles).

The previous goal turn made concrete progress: V167's complete response gain and
quiet costs were published and pushed, and the retained training audit showed
limited joint fine-family coverage. This turn implements a data-distribution
experiment rather than another loss coefficient change.

The [V168 protocol](../docs/fine-mesh-training.md) fixes both heads to the V167
bounded architecture and losses. Of 341 mesh batches, the even ordinal batches
(171) transport both nominal periods from 6–32 to 6–10 pixels, and the contrast
quantile into four bands: .02–.05, .05–.125, .125–.25 and .25–.4. Counts are
86/86/85/85 pairs. This jointly changes period and contrast, not either factor
in isolation. All 659 nonmesh and 170 other mesh batches retain original inputs
and parent predictions. Cameras, CFA, geometry, level, tint, slopes, widths,
orientations, phases, masks, exposure, noise coefficients and seeds stay fixed.
All 342 new empty clean targets match their originals exactly. Poisson rates
change, so a matching seed does not promise identical noisy empty pixels.

The renderer exactly replays legacy pixels without global RNG changes. All 22
new meaningful data tests and 288 total relevant CPU checks pass (4.58 seconds).
All 90 neural sources match V167, with no new neural module. Six original input
batches (steps 1/12/17/19/82/105) were generated once, actually viewed in six
native boards, and adopted into the cache. The boards cover all contrast bands,
ADC-only and ISO12800; faint wires remain noisy while stronger examples show
coherent crossings. They contain clean/noisy/empty data, not denoised results.

The independent data audit checks all 171 changed batches, 342 clean sensor
fingerprints and 342 exact old empty targets. Among 322 changed noisy pairs,
median signal RMS rises from 2.32196 to 10.71058 DN16; median full-context input
signal/noise energy ratio rises from .00732094 to .03804274. The 20 ADC pairs
stay separate. The energy proxy is not detectability or restored-RGB covariance.
171 new masks use independent streaming NumPy extrema; 829 unchanged candidate
masks retain the old independent oracle. Actual future training must match
both arms' masks and data-specific units, rather than assert identical values.

The original cache worker omitted the archived deterministic-algorithm flags.
It disabled TF32/benchmarking but did not set cudnn.deterministic or deterministic
algorithms. A separate validation pass checked every one of its 171 new input
batches under the archived settings, finding differences in all 171 parents,
maximum .00463860 DN16. Corrected parent arrays are canonical for training. Both
passes, all sources/receipts and original arrays are preserved. No input/noise
was regenerated. This is 342 parent/backbone roots and 1,368 images each, including
171 deliberate setup-validation calls. It retains about 2.00 GiB of corrected
parents beyond the initial 5.34 GiB cache. No head training restart occurred.

The original head controller and review queue are live. Genuine 8+2 restoration
passes; all ten control rows reproduce V167 bounded-head traces. Smoke has 94
finite Adam states and nonzero maximum gradients for all parameters; minimum
maxima are 3.68087e-11 control and 1.45739e-11 candidate. Peak CUDA allocation
is 6.753074 GiB. Full training's first ten rows match the restored smoke. Both
heads have the same 124909 parameters / 47 tensors and quarter support floor.
Full all-1000 control state/trace replay and quality are pending.

The original review queue is frozen for all 822 cases/four raw/EMA endpoints,
including both protected GFX scenes/priors/windows/JPEGs. It schedules 3288 head
calls, 1644 new candidate arrays and 1644 actual control replays. Head stages
are 20 smoke + 2000 train + 3288 review = 5308 roots / 11368 images. No new neural
compatibility roots are planned because all 90 neural sources match. All 72
native figures / 24 restoration triplets still require actual viewing and
independent pixel verification. ISO100 AHD/JPEGs are qualitative, not exact GT.
All old evidence, held-out identities and original media remain protected.

Published preparation retains 20 exact receipts, 148 source texts, 90 neural
hashes and six viewed data boards. Eleven all-case reducers are frozen before
quality exists, including separate units/masks and thirteen retained versions.
Reserves are 56/116 GiB local/external plus .5 GiB projection margin and .25 GiB
remaining local bound, with 12 GiB CUDA / 52–32 GiB launch/runtime RAM checks.
The preparation verifier must independently check these bindings and prefix
claims before committing. No restoration gain is claimed; the user's combined
fine-detail/flat-field goal remains active.

The first read-only preparation verifier assumed nine NPZ fields instead of eight
plus a separate parent array, then failed its aggregate-count assertion. Its
source and log remain intact. A new verifier version corrects that count to
1368 for 171 batches. Data and scientific workers are unchanged; the correction
receipt preserves both verifier sources. The public verification result is
written only after the corrected check passes.
