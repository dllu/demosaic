# Fresh coloured finite-wire neural benchmark

Recorded: 2026-11-16T22:29:23-08:00 (America/Los_Angeles).

Prepared a new exact coloured multiscale fine-wire cohort to test whether
cleaner-looking joint support preserves actual colour/detail. Two512-native
procedural geometries: neutral increments, and green strong/magenta weak with
sensorRGB weak contrast[1,-.3,.7]. Dominant broad nuisance carriers, distant
bright edge, finite Gaussian subpixel wires,8x8 area integration/no optical
blur. FourCFAs x2 explicit1600/6400 priors x3 independent-noise roles=48.
Distinct source/CFA/prior/role seeds, signed read noise retained; no photo,
protectedmedia/source-drive access or training/weight update.

Seven data tests pass: signed RGB increments, area determinism, actual CFA
site/Poisson-read statistics, independent role keys and negative read noise.
Initial test had one FP32 bright-edge closure difference1.32507e-8 versus
tolerance1.3e-8; retained exact test/log, bounded by two FP32 ULPs far below
1DN16. Numerical generator unchanged. Initial import-sorting lint fixed;
all logs/source preserved.

Dataset/neural plan9374d018157ec40e5d38ebba6738451684dd6ab00b0234a627302cf9d537810d.
Neural owner982940/create1794895861.1 completed all48 cases:48 V120 full
parents+96 genuine masked fields=144 root and144 DINO calls,43.569s excluding
load. Full/masked inference accesses only actual RAW/CFA/WB/matrix, input-
based variance; targets/true variance never loaded. Masked arguments invariant
under actual withheld NaNs, fingerprints/masks saved.91 restoration tensors
and DINO hash unchanged before/after. Fictional fixed WB/matrix declared,
not camera calibration. Parents here V120, unlike older V143 procedural panel;
no across-cohort performance inference.

Prepared four immutable variants using same V120 parents/96 fields: broad,
fine phase, independent fine H1, joint fine H1. Same Hann512/full-frame,
129/32/32-bin guide kernel; fixedt2/all six controls. Primary analytic joint
versus independent fine H1, NN secondary; all192 corrections close before
GT scoring. Intended metrics include weak sensorRGB response, quiet/increment
and colour-orthogonal errors plus per-colour response; grey output alone
cannot count as success. At least two native160 GT triplets/identical ROI/
exposure/calibration required for completed report.

First controller launch mistakenly raced an exec preparer still running;
comparison-plan.json absent, child terminated before its claim/stages. Exact
failure log/receipt retained. Waited on preparer's actual session completion,
validated all four plans, then launched controller983443/create1794896133.83.
No neural call or correction repeated. CPU predictors launched once:
broad983670/create1794896168.76 on8/9;
phase983671/create1794896168.76 on10/11;
independent983672/create1794896168.77 on12/13;
joint983673/create1794896168.77 on16/17.
All four background adoptions/independent audits pass, zero additional NN
calls. Two threads/low priority, RAM48/32GiB, disk96GiB,2h internal predictor
deadline. No automatic restart. No new-cohort target scoring/viewing yet.

103 exact static neural/admission/failure archives and164 frozen sources
preserve original preparation while comparisons run; live progress/logs
excluded. [Protocol](../docs/coloured-fine-wire-benchmark.md) ·
[Exact admission](../docs/results/coloured-fine-wire-admission-v1/publication.json).

Later completion: all four48-case predictors terminated normally, all192
corrections closed before any target scoring. Zero additional neural calls,
all48 input/parent fingerprints match,288 H1 pair checks exact. Two new metric
tests pass before scoring: perfect signed colour gives unit per-channel
response/zero colour-orthogonal error; neutralized/absent weak colour fails
recovery.400 scalar metric rows and40 native boards/triplets are prepared;
19,046,400 crop channels checked with independent display functions and exact
readback. Independent final metric audit/actual40-image viewing and balanced
quality conclusions remain pending, alongside the separate70-image full
guided review. Initial report lint caught an unused variable before execution;
fixed and both lint logs retained. No correction/model replay.
[14 exact completion/source/test/render archives](../docs/results/coloured-fine-wire-completed-pre-review-v1/publication.json)
preserve the later state without changing original admission receipts.
