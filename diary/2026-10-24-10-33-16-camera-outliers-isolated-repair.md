# Localize camera outliers and test existing isolated repair

Recorded: 2026-10-24T10:33:16-07:00 (America/Los_Angeles).

Previous goal turn was progress: f675d21 refreshed V112's current native gallery
and joined all 162 camera scores against stronger pre-upsampled RawNIND. Its
largest individual deficit was −4.70361 dB in the museum scene. This turn
investigates that deficit rather than treating every scalar loss as missing
texture or architectural failure. The hot-pixel/DNG integration is already
merged. Originals, model weights, library/CLI defaults, original benchmark
protocols and the active training recipes remain unchanged.

Fixed four adverse fields before viewing new outputs: the worst V112-minus-
strong-reference crop in each of the four scenes with a negative scene mean.
Recovered the exact original inference source archive and initial EMA/official
Tiny identity. Three new CPU FP32 V112/encoder calls recover unretained outputs;
the fourth V112 and all four stronger-reference predictions are reused. Input
hashes match the original stronger-reference execution; the four original
scalar controls match within the declared .003 dB CPU/GPU tolerance. An initial
preparation path incorrectly assumed the work directory shared the plan's name;
it stopped before any learned execution, and its correction is recorded.

Masked orthogonal DC/nonoverlapping 16/64-pixel block decompositions show that
global channel means explain only .66% of the museum crop's V112 error. One
green sample at crop [272,293] explains 67.24% instead, compared with 13.49% for
the stronger reference's largest sample. Input .9856187 differs radically from
its same-phase median .0020401. An independent Torch64 sum/pooling audit agrees
with the NumPy64 decomposition to 5.56e-17. These are error-energy summaries,
not pure noise/detail frequency measurements or fitted physical registration.

The first residual-analysis draft assumed registered reference CFA phases
matched input phases. Empty R/B overlap in the museum crop caused nonfinite
diagnostics and strict JSON serialization failure. Preserve that source, log,
seven partial files, hashes and original/preserved path map. The corrected v2
analysis uses only actual same-color overlap and saved predictions; no neural
work is repeated. Both corrected native boards were viewed at original
resolution, 32 cells across the four fields and two ROI selections.

Tested the existing isolated detector, sigma 6/ratio 2/minimum excess .005,
without clusters. It changes 57 museum sites and none in the other three
selected fields. One new V112/encoder and one stronger-reference network call
receive the identical corrected input and variance with original conditioning.
Museum PSNR becomes 56.75084 versus 56.82213 dB, shrinking the method gap from
4.70361 to .07129 dB. This identifies a localized outlier response; weights and
architecture have not improved. The two published native 160×160 triplets use
ROIs [192,213,160,160] and [320,102,160,160], the largest input-detected outliers,
common +2 EV/WB/matrix, original noisy preview and independently demosaiced
low-ISO AHD reference accurately labeled approximate, not exact RGB GT.
All 12 comparison cells and the concentration plot were actually viewed.

Extended the unchanged default detector to all 72 known/90 unseen development
camera crops, with identical repaired inputs for both methods. It corrects
973 sites in 63 crops. Reuse 99 unchanged original rows per method and the
already-repaired museum pair; perform exactly 62 new V112/encoder and 62 new
reference-network forwards. All changed inputs/predictions remain retained.
Both panels complete with 162 rows, finite state/source/RNG guards and counts.
The worker wrote complete scientific results at 10:35:58 PDT, but its shell
handle later returned exit 143; no signal was sent by this work, and the cause
is unknown. Preserve both observations instead of claiming a clean shell exit
or retrying the learned work. Independent NumPy64 rescoring verifies all 126
changed-input predictions and 630 fields with maximum primary error 5.72e-6 dB.
SSIM is not independently rebuilt.

Default V112 known mean rises 54.26914→54.40640 dB (+.13726), mainly the museum
scene's +.52715 dB. Unseen rises only 53.95378→53.95404 (+.00026). V112 improves
2/4 known and 2/5 unseen scene means. With repaired inputs for both methods,
V112-minus-stronger-reference is +.13976/+.08847 dB, while four of nine scene
means still favor the reference. Exact empirical scene-bootstrap intervals for
the V112 repair changes are [−.00385,+.39527] / [−.02210,+.02364] dB, enumerating
4^4 and 5^5 scene resamples. They describe this small fixed development set,
without training-seed uncertainty or a broad real-camera superiority claim.

The largest default crop regressions are −.33426 dB in Expedit and −.29709 dB
in 3apples. Two additional original-input V112/encoder CPU captures, necessary
because their float predictions were absent, enable adverse native viewing;
their scalar controls match the original GPU observations. The ten-cell board
was viewed. A single exploratory ratio-8 follow-up, chosen after inspecting
development regressions, corrects 104 sites in 27 crops. It reuses 135 original
rows and eight byte-identical default-repaired prediction pairs per method;
19 new V112/encoder and 19 stronger-reference calls produce the remaining
outputs. This worker exits 0. Independent rescoring verifies its 54 changed
predictions/270 fields to 4.67e-6 dB maximum primary error. V112 reaches
54.39509/53.95563 dB; worst crop drop remains −.29674 dB. It is neither an
independent confirmation nor a threshold sweep, and does not justify choosing
ratio 8 or changing defaults.

Correct the initial interpretation of reference-supported removed points.
Their isolated colored appearance prompted checking fixed full-sensor
coordinates across unrelated captures, using only cached original Bayer inputs.
At [2886,354], the red sample recurs as an outlier in all five Canon M100 scenes
at ISO 1600: excess above same-phase median .15755–.82787, versus −.00842–.02071
in the corresponding higher-ISO captures. [5509,2116] has a similar pattern.
Independent publication code rebuilds all ten capture values for each point.
This strongly supports sensor/capture/preprocessing artifacts; the physical
mechanism is not proven. Calling these two examples established genuine-detail
loss was premature. Historical machine selection/hypothesis strings are
preserved, with this correction made explicit in current docs and the public
receipt. Low-ISO reference support alone cannot establish real scene detail;
retaining a reference defect may improve PSNR. No reference/mask is edited.
Other unresolved single-color lights remain intrinsically ambiguous, and
isolated repair stays optional. The 16-scene reserve remains unscored.

Total successful additional learned work in this turn is 87 V112 restoration
and 87 Tiny encoder forwards, plus 82 stronger-reference network forwards:
3 initial + 1 local repair + 62 full-default + 2 adverse baselines + 19 strict
for V112; 1 + 62 + 19 for the reference. All are CPU FP32. No optimizer update,
new noise observation, RAW decode or CUDA initialization occurs in this study.
The independent metrics cover 180 changed-input predictions/900 fields. The
original four and two extra CPU controls do not bound every unretained original
GPU float. No successful learned result is repeated for report bookkeeping.

Published [current report](../docs/camera-outliers.md),
[machine evidence](../docs/results/v112-camera-outlier-repair-v1.json), native
positive/adverse examples and links from README, current-model, RawNIND and DNG
docs. Executed workers, plans, analysis versions, failures, predictions and logs
are in `.cache/current-quality-20261023-v1/V112-camera-failure-CPU-v1/`,
`V112-hot-pixel-full-camera-CPU-v1/` and
`V112-hot-pixel-strict8-full-camera-CPU-v1/` under the same cache parent.

At 11:18:37 PDT, the final CPU-only verifier checked 673 unique bound files,
all three current training/review plans, 54 native board cells and 12 standalone
triplet cells, including byte equality between the improved triplets and board.
Existing repair code exactly matches the frozen executed source. Preserve
`final-verification-v1.py`, its log and `final-verification-v1.json` locally.
No source/model tests are repeated for documentation and already-audited saved
arrays. A separate check passes all 306 local links in 12 changed Markdown
files and confirms no existing machine receipt, instruction, source, test or
configuration changes. Its local receipt is `documentation-links-v1.json`.
Staged whitespace is checked before committing.

The original GPU controller 867877/1792848017.25 completed V114 Tiny's original
20,000 updates at 11:12:32 PDT. It records 20,000 training/640 validation forwards,
all Adam steps 20,000, finite model/EMA/Adam and frozen official Tiny. Endpoint
SHA256 is 2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2.
Its generic accounting status mistakenly says Small; the worker result arm,
backbone hash and checkpoint confirm Tiny. Preserve the receipt unchanged and
explain the label in the [current training observation](../docs/results/v114-trained-v115-running-v1.json).
V115 fitted Small is now running under child 1165213/1792865572.94, with logged
step 375 in that observation. Evaluator 986158/1792855221.87 and independent
audit 986159/1792855223.35 remain live, waiting on their exact dependencies,
with zero children or completed stages. Update current docs accordingly;
V112 remains the working model until trained endpoint quality is assessed.
About 255 GiB external / 795 GiB internal remained free at 11:17 PDT.

This is meaningful diagnostic/integration progress, not completion of PROMPT.md.
Broad real-camera superiority, faint high-noise fine detail, and 100MP within
10 seconds remain open. Allow the original Small training and retained-output
quality/audit chain to finish; inspect actual native/GFX results before deciding
the next trained fine-detail intervention. Quality continues to precede speed.
