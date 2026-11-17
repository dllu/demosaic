# Fresh coloured fine-wire benchmark

**All192 corrections,400 metric rows and40 native figures are complete;
independent final audit/actual native review and conclusions are pending.**
This follows the observed colour improvement
and synthetic-response cost of [joint fine support](joint-fine-colour-support.md).
Its purpose is to measure true colour/detail recovery on known coloured
signals, including a negative green contrast. This is a new adaptive synthetic
development benchmark, not untouched camera validation or a training update.

Two new512-native procedural scenes contain a distant bright edge, two
dominant broad nuisance carriers and two finite Gaussian wire families with
unequal strengths. Source0 has neutral increments; source1 has a green strong
increment and magenta weak increment with sensor-RGB contrast`[1,-.3,.7]`.
Wire widths0.4–0.55 native pixels, independent phases/frequencies and a finite
envelope are integrated with8×8 subpixel area samples. There is no optical
blur. Broad structure is intentionally stronger than the fine families, so
the original two-candidate budget cannot be assumed sufficient.

The generator seed202611162200 is fixed before correction outcomes. Four CFAs,
RGGB/BGGR/GRBG/GBRG, and two declared priors,1600 shot/read`0.00032/4.096e-7`
and6400 `0.00128/6.5536e-6`, give16 groups × three independent-noise roles =
48 observations. Roles are background, strong direction, then both directions.
Poisson and signed Gaussian read draws use distinct source/CFA/prior/role
keys; there is no paired-noise coupling, clipping of negative read samples or
new seed selected from quality outcomes. True variance is retained for audit,
but inference receives the declared input-based variance proxy only.

Targets are sensor-linear FP32 with16-bit DN reporting. The fixed fictional
WB`[1.55,1,1.7]` and matrix are declared in the generator and archive. They are
not a fitted camera calibration. No photo, protected capture, RAF, JPEG or
source-drive access enters this cohort. All existing protected media/siblings
remain outside training. The current method's standing GFX comparisons remain
in its separate completed report, with independent references labelled not GT.

The new V120 full-input parents and96 genuine A-only fields are complete:
**48 parent +96 masked =144 root and144 DINO encoder calls**,43.57s excluding
initial model loading. Actual masked arguments are invariant to withheld NaNs;
fingerprints and declared masks are saved. All91 restoration tensors and the
DINO backbone match before/after; no optimizer update occurs. Parent and
masked inference load packed RAW/CFA/WB/matrix only, never targets or true
variance. This is fresh synthetic sensor evidence, separate from the zero-
replay48-case development pilots. All parents here are **V120**; earlier
procedural results used V143, so only within-cohort method contrasts are valid.

Four immutable variants reuse exactly those parents/fields and noise draws:
broad-only guided phase; additional fine phase; independent-colour fine H1;
joint-colour fine H1. Hann512/full-frame geometry, native129/stride32,
32 phase bins and all six global/local controls use fixed threshold2.
The primary contrast is joint versus independent **analytic** fine H1,
with NN secondary and raw-H1/broad/phase controls retained. No new neural
forwards are expected during correction. All192 corrections must close
before target scoring, viewing or threshold selection.

The intended report pairs weaker sensor-RGB increment response with absolute
quiet/increment errors and colour-orthogonal/per-colour responses. It must
retain adverse cells and at least two native160 noisy/restored/exact-GT
triplets, ROI`[176,176,160,160]`, display exposure16/contrast1, identical WB/
matrix and coordinates across methods. Grey output or lower colour variation
alone is not a success criterion. Two reused constructed geometries are not
camera-population evidence; no calibrated uncertainty claim follows.

Generator checks pass for signed independent RGB increments, deterministic
area rendering, true CFA coordinates under all four layouts, empirical
Poisson/read means/variances, independent role keys and signed read samples.
Seven tests pass. An initial assertion missed one FP32 bright-edge rounding
element by2.5e-10 beyond its tolerance; the corrected bound is two native
FP32 ULPs, far below1 DN16. The original test source/log and initial import-
sorting lint result are preserved. The numerical generator did not change.

The first comparison-controller launch raced its still-running plan preparer
and terminated before its claim or any stage. After the preparer completed,
all four plans were validated before the replacement launch. Exact failure
log/receipt remain; no neural call or correction was repeated. Current owner
983443/create1794896133.83; CPU pairs8/9,10/11,12/13,16/17, two threads/low
priority. Start/runtime RAM48/32GiB, disk96GiB and two-hour per-predictor
deadlines. No automatic restart.

Root: `.cache/experiments/coloured-fine-wire-neural-v1/`.
Dataset/neural plan:
`9374d018157ec40e5d38ebba6738451684dd6ab00b0234a627302cf9d537810d`.
All four comparison plan identities, fresh neural receipts, source snapshots,
launch/early-failure evidence and physical inputs are retained under that root.
[103 exact admission/neural/failure archives and164 frozen sources](results/coloured-fine-wire-admission-v1/publication.json).

All four predictors subsequently completed normally, zero additional neural
calls.288 raw-H1 pair checks and48 input/parent fingerprints agree across
variants. Scoring source was frozen after two known-target tests (perfect
signed colour, and failure of neutralized/absent weak colour) and after all192
corrections closed.400 metric rows and40 fixed-ROI native figures are now
prepared, with19,046,400 crop channels checked by two independent display
functions and reread exactly. Actual viewing/final independent metric audit
and a balanced quality report remain required.
[14 exact completion/source/test/render addendum archives](results/coloured-fine-wire-completed-pre-review-v1/publication.json)
preserve this later state without rewriting admission receipts.
