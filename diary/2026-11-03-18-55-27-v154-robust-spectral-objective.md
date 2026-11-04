# V154 robust delivered spectral supervision

Recorded: 2026-11-03T18:55:27-08:00 (America/Los_Angeles).

Active preparation recorded: 2026-11-03T19:08:59-08:00 (America/Los_Angeles).

The previous goal turn made progress by completing and pushing V153 in118bd3c:
all3 heads finished1k,all6 endpoints/822 cases/84 native figures and independent
audits were completed. Delivered-output spectral MSE gained mesh response but
worsened blank/quiet/natural/ADC tradeoffs,without new convincing real crossings.
Those results motivate testing a different penalty rather than treating
placement or stronger correction as a solved fine-detail problem.

Implemented the [V154 robust spectral comparison](../docs/robust-spectral-objective.md).
Three identical fresh relative-phase heads retain33,713 parameters/13 tensors,
all86 neural source files and the same inference inputs. The delivered-RGB
spectral term compares V153 MSE with Charbonnier epsilon .01/.003 in repeated
RAW frame-noise proxy units. Stable rationalization preserves tiny powers and
finite zero derivatives. The coefficient stays .25; penalty shape and effective
gradient strength change together,not equal-norm objectives. Weak nonzero
coefficients get more relative pressure,including erroneous band coefficients
in flat targets. Large-error pressure falls relatively; affine/DC and frequencies
outside the existing band remain outside this term,with RGB pixel loss retained.
The frame scales are training units,not calibrated post-demosaic covariance/SNR.
Targets remain training/scoring/display-only,never forward inputs.

All4,000 old cached observations/parents/noise/geometry are reused:882 supervised
batches /3,528 observations per arm,118 zero-ADC gradients and1,000 AdamW/EMA
clocks. Data/domain weights,physical inputs,initialization,band/bound/support,
LR/schedule/clipping/EMA match. MSE control must reproduce V153 delivered-RGB
trace,raw/EMA/Adam and all1,644 final control arrays. The six fixed raw/EMA
endpoints are declared at1k; there is no early epoch selection or quality claim.

Twenty-seven focused tests pass in .80s. Independent NumPy dense-DFT/weighted
plane-projection operators check both robust epsilons and full output adjoints
on two-image nondivisible rectangular batches across4CFAs and zero/positive
scales. Other checks cover exact RGB-MSE values/gradients,tiny complex errors,
finite first/second derivatives at zero power,relative weak-error pressure,
flat-target and unsampled-color penalties,support gradients and invalid epsilons.
These are operator/objective evidence,not native restoration or flat-safety proof.

Frozen training imports pass. Current/frozen V153 relative forwards match28
archived contexts,56 actual evaluations. All three ten-update discarded CUDA
checks pass with genuine8+2 model/EMA/Adam/RNG restoration,seven supervised and
three zero-ADC steps each. All39 named tensors receive finite nonzero gradients
over the prefix. Peak allocated CUDA is4.15GiB. Production starts fresh and
MSE-control loss/component/norm/LR rows replay V153 exactly at every completed
step. Original controller PID3122545(created1793761000.14 UTC epoch),worker
PID3122632(created1793761033.03),no scientific failure or restart. An immediate
status read raced initial file creation; the registered PID was rechecked and
the same run continued. No process was restarted from that observation race.

Checkpoint250 audit proves all39 finite Adam states and exact MSE-control raw,
EMA,complete optimizer and first250 trace rows. The immutable active snapshot
records294 exact control rows and33 zero-loss/zero-norm ADC rows per arm,with
three exact PID/create-time owners verified live. Parity/smoke owners are
terminal. Queued postprocessor PID3123510(created1793761137.67 UTC epoch) waits
on the original training owner. All six frozen entrypoints pass import checks.
Unlike the initial V153 workflow,it mandates actual-final-checkpoint validation
and strict CPU loading before any review claim/endpoint forward,and retains
failed-child metadata. No reviewer has run on incomplete weights.

There was insufficient internal space for another full local13.263GiB output
set while retaining96GiB. The plan instead places the two MSE-control endpoints
(4.421GiB) locally and four robust endpoints (8.842GiB) on the external SSD.
Actual filesystem-device IDs differ; all paths stay in newly owned directories.
Initial free space was108.56/222.45GiB; runtime reserves remain96/208GiB. No old
evidence was deleted or moved. Every export/prediction binding records its real
path/hash. All training inputs stay in the local hot cache. RAM52GiB launch /
32GiB runtime and CUDA12GiB quota remain. External output root:
`/mnt/external/demosaic/quality-20261103/V154-robust-spectral-v1/`.

[Preparation evidence](../docs/results/v154-robust-spectral-preparation-v1.json)
preserves14 byte-exact receipts and19 source texts,all86 unchanged neural hashes,
storage plan,checkpoint250 and historical294-row live snapshot. Final training,
all six endpoint quality collections,independent metrics and actual native
viewing remain pending. Planned quality:4,932 actual head forwards,84 native
figures/36 repeated-cell triplets. Actual blank/quiet errors,noisy flats,
retained/organic photos,ADC photos/slopes and both standing real scenes/priors/
windows/JPEGs remain. Real ISO100/AHD/JPEG references differ in aperture,shutter,
processing and motion:qualitative,not exactGT,and never scored. Captures,JPEGs,
siblings and validation sources remain excluded from training. No new parent/
DINO/noise calls,original lookup,RAW decode or dataz access; originals read-only.

README and research/model/experiment indices link the active trial without
claiming improvement. V153's stronger response,V151/V152 quieter controls,V150
ADC restoration and V120/general plus explicit V143 periodic detail keep their
measured roles. Next verify these same live handles,finish the declared six
endpoint comparisons and inspect the native crops. The broad requested dark/
low-contrast-detail and clean-sky goal remains active.
