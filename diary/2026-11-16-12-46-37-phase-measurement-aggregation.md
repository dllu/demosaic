# Phase-aligned measurement aggregation

Recorded: 2026-11-16T12:46:37-08:00 (America/Los_Angeles).


Previous turn was concrete progress: published complete three-prior wave and
V131 broad audits and the opt-in fixed ADC repair. The new turn revalidated the
original V132 controller/worker/reviewer by PID+creation identity; at11,600/20k
the worker remains live, with about89GiB available RAM. No worker was signaled,
restarted or had its source/horizon changed.

The ADC follow-up demonstrates why amplitude alone remains insufficient:
weakest-band response improves while error worsens. The next intervention
implements literature proposal4, measurement aggregation instead of a richer
free waveform. Reviewed the primary NLFeMF2604.17453v1 and IDF2508.19649v1 pages.
This prototype is our analytic RAW/CFA experiment, not a reproduction of either
learned method and not an inference from their benchmark rankings.

Added `phase_aggregation.py`: original A-only H1 edge/frequency/noise/competing-
direction fits, then same-color circular phase histograms within129-native-pixel
spatial windows. Fixed32bins, linear splatting/interpolation, circular
[1,2,3,2,1]/9 weights and16-pixel query grid. Source/query stay on the same side
of the A-only fitted edge. The phase-conditioned and unconditioned local means
are normalized nonnegative averages; their difference is signed. No convex
output/range or noisy-flat safety claim is made. Each direction/color receives
its own A/B conditional support. Current cardinality matching is shared with
the H1 control. Only after scoring does the fixed linear detail operator read
the parent innovation, avoiding component doubling.

Direct independently enumerated weights, four CFAs, actual NaN withholding,
color isolation, edge stopping, linearity, constant annihilation, exact-parent
identity, native even boundary axes, ADC bypass and byte-exact H1 control checks
are covered. The first test run had23 passes/four boundary-test failures from
using the production256 minimum in a32-pixel fixture; corrected the test to
pass its explicit geometry and separately assert the production rejection.
No numerical threshold was relaxed. Production defaults are frozen singletons;
phase coordinates are bounded below the upper circular endpoint. Combined
27 new/68 existing tests pass95 total in4.64s. Ruff passes.

Prepared frozen `phase-aggregation-pilot-v1`:36 finite-role images from sources0/1,
RGGB/repeat0, near/far at400/1600/6400, plus12 original material/main-GFX/cab
contexts. This48-input study uses matched H1 controls from the exact same A-only
fits, fixed0/2/4 threshold sweep, primarylocal2. It performs zero neural/DINO,
source/noise construction, RAW decoding or training work. All outputs close
before any target/reference scoring. Frozen controller506734/1794862019.85 and
worker506735/1794862019.88 are confirmed live, first two cases closed in34.56s.
Resource floors32GiB RAM/96GiB internal free, one-hour prediction budget. No
quality gain is claimed before completion/audit/native viewing.

The legacy pilot reporter now checks the complete declared ID set rather than
hardcoding24. After launch, source inspection found the legacy independent
finite-score join omits noise profile, which would collide in the expanded
three-prior study. Fixed the current public auditor to include profile and
reject duplicate identities. The producer's already frozen source stays intact;
its prediction/report evidence remains valid. A separately frozen postprocessing
addendum will use the corrected join after the original controller terminates;
no prediction replay or receipt replacement is permitted.

The corrected profile-aware auditor also passes the original24-case H1 cohort:
679 metric fields,28 finite rows,28 native boards/9,216,000 RGB channels, maximum
score/finite discrepancy zero and material-band discrepancy2.50e-15. This is a
backward-compatibility check of the reporting change, not new inference/quality.
The new pilot reached27/48 complete cases while its exact worker stayed live.
Postprocessing watcher507386 is separately frozen and waits for terminal closure;
it will preserve the known original auditor failure and run the corrected join,
then make explicit H1/aggregation comparisons and six correction-max stress views.

The first arm completed all48 outputs/412 tiles/824 A-only fits in818.46s.
As anticipated, its frozen legacy audit failed the profile-less join; no
prediction or report was repeated. The separate corrected audit passes2,613
metric fields/156 finite rows and14,131,200 native RGB channels across44
original boards. Score/finite discrepancy is zero, material-band maximum
2.94e-15. The matched/stress reporter independently checks3,532,800 new or
inserted native channels. All24 overlapping H1 cases/144 prediction arrays
match the earlier completed matching study exactly with identical input hashes.

The result improves response but not fidelity. At400/far, matched H1 local2
weak response2.801%→aggregation12.614%, strong43.332%→65.988%. Quiet RMS
4.02596→4.24421DN16 (+5.42%), weak-increment error11.80386→12.03450 (+1.95%).
Full-image RMS falls21.72125→21.56611. Source1 drives the weak gain4.592→23.601%;
source0 only1.011→1.627%. Both quiet and increment errors worsen versus H1 in
all six cells; local support remains better than aggregation's own global
support. At6400/far weak response becomes negative. Absolute edge-only role0
error also worsens in every cell; all468 per-role/source/method/cell rows are
retained, with MSE=DC+spatial identity checked. Ordinary bark/fur changes are
−.00680/−.04459dB versus V120; four ADC/faint controls remain exact identities.

Actually viewed all22 matched H1 comparisons, six maximum-correction stress
boards, two400/far noisy/aggregation/GT triplets and both plots:32 initial-arm
views. Higher priors remain mostly flat. Sky is unchanged, foliage painted,
coarse fence gains unwanted modulation. The building stress ROI[76,260,160,160]
has severe new green/magenta bands, correction RMS410.30DN16 versus V120; this
is correction magnitude, not reference error. Both cab priors retain stronger
modulation with incomplete crossings. Both ISO100/AHD/JPEG families keep their
qualitative-not-GT labels; original media and siblings stay untouched/excluded.

A source-only censor decomposition reproduces the complete original building
prediction byte-exact. Its34 saturated samples/262,144 native sites contribute
only13.60DN16 RMS in that failure ROI; removing their direct contribution leaves
409.88DN16. Saturated-versus-total projection is.001571. This rules out that
simple direct-innovation explanation, not possible saturation effects on
geometry/weights/support. No target/reference was read; zero neural work.

Found a conceptual mismatch: validation removes the A-only conditional null,
but delivered Q(raw−parent) did not project the parent's nuisance component in
the same way. Added explicit `parent_projection` policy. Original `innovation`
remains available; current default `conditional_null` delivers
Q(I−Pnull)(raw−parent) using the fixed design/noise weights after scoring.
Four additional CFA checks reproduce the exact validation null, exclude actual
withheld values and annihilate its full affine/step/competing-wave span. All99
combined tests pass in4.72s; no numerical tolerances relaxed. This is algebraic
consistency, not an image-quality gain. The input-only building check keeps H1
byte-exact and changes the failure correction410.30→411.88DN16: bands persist.
Viewed two unique no-reference building boards; the third max-ROI board repeats
the same coordinates/pixels and is not claimed as separately viewed.

Launched separately frozen `phase-aggregation-projected-pilot-v1`, controller
510186, worker510187/1794863702.51; reviewer510188. The same48 inputs/geometry/
validation/thresholds/parents are used, with corrected profile joins already
frozen. No old source/output is changed and no neural prediction is replayed.
The first five cases close in90.12s; both controller/reviewer are confirmed
live. Original V132 worker remains the same224010/1794843486.14, observed
step13,350 with training/validation still active. The broader weak-detail goal
remains unresolved; no completion/promotion claim is made.

Published `docs/phase-measurement-aggregation.md`,72 initial native boards,
two tradeoff plots, three input-only projection-check boards and exact source/
receipt archives. The first33 archive payloads and18 addenda preserve old bytes,
including failed fixture/audit attempts. README/current choices/experiment/
research/diary indexes retain the useful low-prior response gain and material
costs explicitly. Conditional-projection full quality is still pending.
