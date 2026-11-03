# Refit accepted wave amplitudes without expanding support

Recorded: 2026-11-03T00:10:25-08:00 (America/Los_Angeles).


The previous goal turn was progress: commit `9720e72` published reciprocal green
support, fresh validation and 37 native boards. Its stricter support also loses
real contrast, and average mesh response remains far below the exact target.
This study uses `.cache/quality-20261103/supported-amplitude-v1`; `/mnt/dataz`
and original photographs remain untouched.

The first hypothesis is redundant shrink after support selection. The current
path attenuates globally and with a local power proxy before applying the final
reciprocal mask. Development compares that exact baseline with removing only
the global attenuation, removing global/local positive attenuation while keeping
selection and magnitude caps, and bounded joint amplitude refitting of the
already supported/apron-applied waves. The refit uses both measured green
residuals with per-phase affine nuisances eliminated, scalar bounds [0,3], and
shares gains across the existing RGB waves. Frequencies and per-wave spatial
support remain fixed. Same-data selection/refitting is not calibrated confidence.

The first prototype required unavailable SciPy and failed. Its source, failed
logs and partial outputs remain archived. The corrected version uses NumPy
coordinate minimization with an explicit relative box-KKT tolerance. Twelve
independent dense active-set comparisons cover all CFAs, heteroskedastic weights,
interior/lower/upper solutions and isolation from other CFA colors; they pass.
These are algebra fixtures, not new sensor-noise controls or neural calls.

The earlier cross validation is now development: the same 64 recipes and 512
actual neural parents are reused, with no new draws or model calls. Every
complete baseline output is compared bit-for-bit with its preserved cross
prediction. The eight centered real-photo crops are exploratory, not complete
frame outputs. Their initial native views show stronger mesh contrast under
both priors, with little change in inspected building/foliage. Known 1938/GRBG
keeps zero added exact-blank values under all three variants while image RMS
falls from 18.47465 to 17.40820/17.26317/17.89533 DN16. These development findings
do not establish performance on new observations or broad photographic quality.

Partial changed-case results show that stronger amplitudes also amplify faint
blank-support spill. A second development ablation erodes each per-wave Boolean
support by eight native pixels (one existing mask-knot spacing, square
neighborhood, false exterior), then uses either the unshrunk wave or the bounded
refit. This choice was made before any new validation draws. Twelve direct
neighborhood comparisons verify the erosion independently. The native pilot
shows loss of true boundary texture, so this is not assumed to be an improvement.
All prototype versions, pilots and partial/failed runs remain preserved.

The numerical background for separating support from contrast includes
[Deledalle et al., CLEAR (2017)](https://arxiv.org/abs/1606.05158).
This experiment does not implement CLEAR or inherit its guarantees; it tests
specific fixed-wave changes in this same-data RAW pipeline.

The first full development sweep ended with SIGTERM/exit 143 after the completed
prefix through index 480. Outputs remain intact. A separate recovery run rescored
those 481 completed cases from their stored changed predictions or exact unchanged
parent, then executed the final 31; durable per-case rows now prevent losing its
result. An independent ten-column affine/template and direct error/blank/DC/block
check verifies all 2,560 rows. The separate erosion sweep completed normally and
passes the same independent 2,560-row audit. No draws or neural calls were added
by recovery or repeated analysis.

Global-shrink removal alone raises mean response 20.1% and reduces image RMS 0.82%
versus cross on the reused 64 recipes. All 44 changed cases gain response,42 lower
image error and two regress (maximum+.01002 DN16). Mean/worst added blank RMS rise
44.3%/13.3%, with worst .04578→.05186 DN16. All 256 absent parents remain exact.
Removing both global/local shrink improves RMS more but raises worst spill to
.12790 DN16. Joint refit gives higher response but five image-error regressions,
maximum+.26108 DN16. Refit after 8pixel erosion reduces mean spill but loses true
boundary texture:16 image-error regressions, maximum+1.03490 DN16. Those alternatives
remain archived and are compared directly, rather than concealing their losses.

The chosen new `detail` mode therefore keeps the original positive global gate
as selection, then divides each admitted wave by that gate only inside the
unchanged reciprocal Boolean support. Local sparse-TV, local power shrink 9,
magnitude cap 3, masks, frequencies, floor, apron and blend stay fixed. Clipped
windows preserve the exact earlier amplitude policy; short images preserve
Sparse. The stage remains opt-in; its default is still Edge.

The policy was locked before any new validation draws, SHA256
`c57ecbb754a0b87e13736e782fd9d09972f4341af84ef635cb3d7195b2eb0f0a`.
Fresh 64 mesh/empty recipes (seeds 2026112300–2363) add 512 actual V1435k/DINO calls.
Eight preselected Commons val sources add 64 actual calls with native center 512
crops and two declared variants: mean linear-sRGB.02/contrast.125, and mean.003/
contrast 1, each on all 4 CFAs. Sources come from read-only linear RGB16 bin 8 caches,
with no resize; chosen IDs are absent from train rows in the main/reference
photographic manifests. Sixteen clean-target transform checks pass before noise
generation. These additional photographic targets broaden the test beyond the
procedural lattice; they are exact constructed targets, not exact physical scene
references. Total 576 new observations/576 actual forwards are complete, with model,
backbone, input and RNG checks. Fresh postprocessing and three full GFX renders
are running from separate frozen source snapshots.

All 148 phase tests pass (the 57 focused integration checks are a subset), covering
conditional amplitude ratios/support, physical RGB transport, inactive masks,
all CFAs, clipped/small fallbacks and the CLI/RGB16 path. Current source matches
the 80-module full-frame snapshot. No original/RAF decode, training update or
source-drive access was added. Complete-frame and fresh quality conclusions are
pending; broad fine-detail/SOTA/flatness/speed goals remain unachieved.

Fresh validation is now complete. Detail response is .070898 versus Cross.056102
(+26.37%); full 512 image RMS 8.586126 versus 8.673413 DN16 (−1.006%), central spatial
RMS 12.187164 versus 12.393401 DN16 (−1.664%). Mean added exact-blank RMS rises
.000447329→.000635569 DN16 (+42.08%); worst .105353→.135258 DN16 (+28.39%). All 55
changed present cases gain response;54 lower image RMS and one regresses by
.00545 DN16. All 256 absent cases retain parent values. Maximum added blank-pixel
values are 15.06 DN16 (Cross 11.73, Wide 25.12), so low regional RMS does not imply
no false pixels. Native amplified views still show stripe continuation and seams.
All 64 native photographic controls stay unchanged; bark/feather oversmoothing
and broader nonperiodic texture remain unresolved.

The selected rule is better than Wide on this same new set: response+15.28%,
full image RMS−.179%, mean/worst added blank RMS−94.53%/−84.75%. Per-image costs
remain:22 present cases worsen in image RMS versus Wide. Fresh masks cap in
198/228 solves at 8192 iterations; maximum relative gap 2.10e−5 and absolute gap
.003407. These are bounded estimators, not fully converged or calibrated support.

A matched comparison to the actual earlier optional default Edge reuses all 576
parents/draws, with zero new neural calls or noise draws. Detail response rises
52.98%, image RMS falls 1.967%, central spatial RMS falls 3.429%, and mean/worst
added blank RMS fall 92.90%/70.54%. All 55 changed present cases improve both
response and image RMS;201 are unchanged. Edge changes three dark photo inputs:
two tiny improvements and one+.00636 DN16 regression, with no aggregate gain.
This comparison combines preceding context/floor/support work and the new
amplitude policy; it is not an isolated amplitude ablation or another holdout.
An independent 1,728-row audit verifies it. The earlier default is not frozen by
historical promotion rules: Detail is now the CLI/Python API default within the
explicitly enabled periodic stage. Ordinary inference still leaves the stage off.
V120 remains the broadly measured general neural recommendation.

The first release shadow test hit its copied package's authorized-output root;
the next setup lacked the chosen temporary parent. Those failed logs remain
intact. With a temporary directory inside that package, all 149 tests pass. The
actual public package also passes 149 phase tests, including the default CLI/API,
physical seams, inactive support, all CFA layouts, and clipped/small fallbacks.
A release AST audit proves 78 modules byte-identical to the complete-frame source;
the two other modules change only their envelope defaults and API docstring.
All explicit-mode computation is identical. No new numerical tuning was made.

All 576 whole 512 public outputs match the locked prototype in Wide/Cross/Detail:
1,358,954,496 RGB values exact. Independent metrics verify 2,304 primary rows;
four active actual-parent patches cover all CFAs with CPU/CUDA maximum difference
3.47e−18 and unchanged RNG. Three complete 101,995,852pixel renders improve mesh
contrast under both priors, while foliage/building/highlight limits remain.
The sky box keeps all 8,640,000 parent channels. All context records and TV/support/
mask solve, cap and iteration counts match the prior Cross frames exactly.
Correction-only concurrent times are 1342/1619/1632s, still far from 100MP/10s.

The final 53 native boards were actually viewed:41 initial boards plus 12 matched
Edge comparisons. Cached full Edge records bind the identical RAW, actual parent,
noise and checkpoint metadata. Independent PNG checks verify 26,880,000 channels.
All 917,962,668 linearRGB16 export channels match clip/round/orientation; sRGB16
is within 1DN of independentFP64 with ICC/16-bit metadata verified. The supplemental
PNG audit reuses unchanged TIFF checks with all 6 hashes rechecked. A first audit
was started before its dependent report existed; that failed log and the successful
retry remain preserved. Existing boards/receipts were not rewritten.

Two bookkeeping clarifications preserve original evidence bytes. The v 3 pilot
inherited a same-support description although its core variants erode support;
a separate scope-correction receipt states this explicitly. The first default
summary accidentally chose the parent row for aggregate percentages; raw results,
paired counts and independent audits were correct. Version 2 explicitly selects
methodDetail, and a correction receipt links both immutable summaries. README and
reports use the corrected method-specific values.

README, current guides and the new supported-wave-amplitude report now show the
best useful choices, exact-GT triplets, standing scene, both mesh priors/JPEGs,
nonperiodic controls and failure views. Earlier reports retain their numbers,
images and machine receipts, with current-default notes. The publication includes
53byte-identical native boards and 48byte-identical JSON receipts plus original logs.
No training updates, V120 calls, real RAF decodes, original writes or dataz access
were added. This is meaningful progress, not completion: weak/nonperiodic detail,
partial orientation recovery, false boundary structure, seams, bright color and
speed still require work. The goal remains active.
